from flask import Flask, render_template, request, jsonify
import numpy as np
import re
import traceback

app = Flask(__name__)
app.secret_key = 'simplex_solver_secret_key_2024'

class SimplexSolver:
    def __init__(self):
        self.c = []  # Coeficientes de la función objetivo
        self.A = []  # Matriz de restricciones
        self.b = []  # Vector de términos independientes
        self.tipos_restricciones = []  # "<=", ">=", "="
        self.tipo = ""  # "max" o "min"
        self.variables_originales = 0
        self.tableau = None
        self.basic_vars = []
        self.iteracion = 0
        self.variables_holgura = 0
        self.variables_excedente = 0
        self.variables_artificiales = 0
        self.M = 1000  # Valor grande para variables artificiales
        self.es_dual = False
        self.pasos_solucion = []
        self.problema_original = {}
    
    def convertir_numpy_a_python(self, obj):
        """Convertir objetos NumPy a tipos nativos de Python para JSON"""
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, dict):
            return {key: self.convertir_numpy_a_python(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.convertir_numpy_a_python(item) for item in obj]
        else:
            return obj
    
    def parsear_expresion(self, expresion):
        """Parsear una expresión matemática y extraer coeficientes"""
        try:
            expresion = expresion.replace(" ", "").lower()
            variables = re.findall(r'[+-]?[0-9]*\.?[0-9]*x[0-9]+', expresion)
            
            if not variables:
                raise ValueError("No se encontraron variables en la expresión")
            
            nums_variables = []
            for var in variables:
                num = re.search(r'x([0-9]+)', var)
                if num:
                    nums_variables.append(int(num.group(1)))
            
            max_var = max(nums_variables)
            coeficientes = [0] * max_var
            
            for var in variables:
                match = re.match(r'([+-]?[0-9]*\.?[0-9]*)x([0-9]+)', var)
                if match:
                    coef_str = match.group(1)
                    var_num = int(match.group(2))
                    
                    if coef_str == '' or coef_str == '+':
                        coef = 1
                    elif coef_str == '-':
                        coef = -1
                    else:
                        coef = float(coef_str)
                    
                    coeficientes[var_num - 1] = coef
            
            return coeficientes, max_var
        except Exception as e:
            raise ValueError(f"Error al parsear expresión '{expresion}': {str(e)}")
    
    def parsear_restriccion(self, restriccion):
        """Parsear una restricción completa"""
        try:
            restriccion = restriccion.replace(" ", "")
            operadores = ['<=', '>=', '=']
            operador = None
            
            for op in operadores:
                if op in restriccion:
                    operador = op
                    break
            
            if not operador:
                raise ValueError("No se encontró un operador válido (<=, >=, =)")
            
            partes = restriccion.split(operador)
            if len(partes) != 2:
                raise ValueError("Formato de restricción inválido")
            
            lado_izq = partes[0]
            lado_der = partes[1]
            
            coeficientes, num_vars = self.parsear_expresion(lado_izq)
            
            try:
                valor_der = float(lado_der)
                if valor_der < 0:
                    raise ValueError("El término independiente debe ser no negativo")
            except ValueError:
                raise ValueError("El lado derecho debe ser un número")
            
            return coeficientes, operador, valor_der, num_vars
        except Exception as e:
            raise ValueError(f"Error al parsear restricción '{restriccion}': {str(e)}")
    
    def configurar_problema(self, funcion_objetivo, tipo_optimizacion, restricciones):
        """Configurar el problema desde la interfaz web"""
        try:
            print(f"=== CONFIGURANDO PROBLEMA ===")
            print(f"Función objetivo: {funcion_objetivo}")
            print(f"Tipo: {tipo_optimizacion}")
            print(f"Restricciones: {restricciones}")
            
            self.tipo = tipo_optimizacion
            self.pasos_solucion = []
            
            # Parsear función objetivo
            self.c, self.variables_originales = self.parsear_expresion(funcion_objetivo)
            
            # Parsear restricciones
            self.A = []
            self.b = []
            self.tipos_restricciones = []
            
            for i, restriccion in enumerate(restricciones):
                if restriccion.strip():
                    coef, operador, valor, num_vars = self.parsear_restriccion(restriccion)
                    
                    if num_vars > self.variables_originales:
                        self.variables_originales = num_vars
                        while len(self.c) < self.variables_originales:
                            self.c.append(0)
                    
                    while len(coef) < self.variables_originales:
                        coef.append(0)
                    
                    self.A.append(coef[:self.variables_originales])
                    self.tipos_restricciones.append(operador)
                    self.b.append(valor)
            
            # Ajustar todas las restricciones al mismo número de variables
            for i in range(len(self.A)):
                while len(self.A[i]) < self.variables_originales:
                    self.A[i].append(0)
            
            while len(self.c) < self.variables_originales:
                self.c.append(0)
            
            # Guardar problema original
            self.problema_original = {
                'c': self.c.copy(),
                'A': [fila.copy() for fila in self.A],
                'b': self.b.copy(),
                'tipos': self.tipos_restricciones.copy(),
                'tipo_opt': self.tipo
            }
            
            self.pasos_solucion.append({
                'tipo': 'original',
                'titulo': 'Problema Original',
                'c': self.c.copy(),
                'A': [fila.copy() for fila in self.A],
                'b': self.b.copy(),
                'tipos': self.tipos_restricciones.copy(),
                'tipo_opt': self.tipo
            })
            
            print(f"=== FIN CONFIGURACIÓN ===")
                
        except Exception as e:
            print(f"ERROR en configurar_problema: {str(e)}")
            raise ValueError(f"Error al configurar problema: {str(e)}")
    
    def aplicar_dualidad(self):
        """Aplicar dualidad correctamente"""
        try:
            print("=== APLICANDO DUALIDAD ===")
            
            # Guardar el problema original
            c_original = self.c.copy()
            A_original = [fila.copy() for fila in self.A]
            b_original = self.b.copy()
            tipos_original = self.tipos_restricciones.copy()
            tipo_original = self.tipo
            
            # PASO 1: Convertir a forma estándar para dualidad
            print(f"Paso 1: Convertir problema {tipo_original.upper()} a forma estándar")
            
            A_convertida = []
            b_convertida = []
            tipos_convertida = []
            
            if tipo_original == "max":
                # Para MAX: todas las restricciones deben ser <=
                for i, tipo in enumerate(tipos_original):
                    if tipo == "=":
                        # Igualdad: crear dos restricciones
                        A_convertida.append(A_original[i].copy())
                        b_convertida.append(b_original[i])
                        tipos_convertida.append("<=")
                        
                        fila_negativa = [-coef for coef in A_original[i]]
                        A_convertida.append(fila_negativa)
                        b_convertida.append(-b_original[i])
                        tipos_convertida.append("<=")
                        
                    elif tipo == ">=":
                        # Convertir >= a <= multiplicando por -1
                        fila_nueva = [-coef for coef in A_original[i]]
                        A_convertida.append(fila_nueva)
                        b_convertida.append(-b_original[i])
                        tipos_convertida.append("<=")
                        
                    else:  # "<="
                        A_convertida.append(A_original[i].copy())
                        b_convertida.append(b_original[i])
                        tipos_convertida.append("<=")
                        
            else:  # "min"
                # Para MIN: todas las restricciones deben ser >=
                for i, tipo in enumerate(tipos_original):
                    if tipo == "=":
                        # Igualdad: crear dos restricciones
                        A_convertida.append(A_original[i].copy())
                        b_convertida.append(b_original[i])
                        tipos_convertida.append(">=")
                        
                        fila_negativa = [-coef for coef in A_original[i]]
                        A_convertida.append(fila_negativa)
                        b_convertida.append(-b_original[i])
                        tipos_convertida.append(">=")
                        
                    elif tipo == "<=":
                        # Convertir <= a >= multiplicando por -1
                        fila_nueva = [-coef for coef in A_original[i]]
                        A_convertida.append(fila_nueva)
                        b_convertida.append(-b_original[i])
                        tipos_convertida.append(">=")
                        
                    else:  # ">="
                        A_convertida.append(A_original[i].copy())
                        b_convertida.append(b_original[i])
                        tipos_convertida.append(">=")
            
            # Guardar paso de conversión
            self.pasos_solucion.append({
                'tipo': 'dualidad_paso1',
                'titulo': f'Paso 1: Conversión a forma estándar para dualidad',
                'c': c_original,
                'A': A_convertida,
                'b': b_convertida,
                'tipos': tipos_convertida,
                'tipo_opt': tipo_original
            })
            
            # PASO 2: Crear el problema dual
            print("Paso 2: Crear problema dual")
            
            # Cambiar tipo de optimización
            nuevo_tipo = "min" if tipo_original == "max" else "max"
            
            # Los coeficientes del dual son los términos independientes del primal
            c_dual = b_convertida.copy()
            
            # Transponer la matriz A
            num_restricciones_convertida = len(A_convertida)
            num_variables_original = len(A_convertida[0]) if A_convertida else 0
            
            A_dual = []
            for j in range(num_variables_original):
                fila_dual = []
                for i in range(num_restricciones_convertida):
                    fila_dual.append(A_convertida[i][j])
                A_dual.append(fila_dual)
            
            # Los términos independientes del dual son los coeficientes del primal
            b_dual = c_original.copy()
            
            # Determinar tipos de restricciones del dual
            if tipo_original == "max":
                # MAX → MIN: restricciones del dual son >=
                tipos_dual = [">=" for _ in range(num_variables_original)]
            else:  # "min"
                # MIN → MAX: restricciones del dual son <=
                tipos_dual = ["<=" for _ in range(num_variables_original)]
            
            # Guardar paso del dual
            self.pasos_solucion.append({
                'tipo': 'dualidad_final',
                'titulo': f'Paso 2: Problema Dual ({nuevo_tipo.upper()})',
                'c': c_dual,
                'A': A_dual,
                'b': b_dual,
                'tipos': tipos_dual,
                'tipo_opt': nuevo_tipo
            })
            
            # IMPORTANTE: Actualizar el solver con el problema dual
            # Ahora el problema dual se trata como un problema primal normal
            self.c = c_dual
            self.A = A_dual
            self.b = b_dual
            self.tipos_restricciones = tipos_dual
            self.tipo = nuevo_tipo
            self.variables_originales = len(self.c)
            self.es_dual = True
            
            print("=== DUALIDAD APLICADA CORRECTAMENTE ===")
            
        except Exception as e:
            print(f"ERROR en aplicar_dualidad: {str(e)}")
            raise ValueError(f"Error al aplicar dualidad: {str(e)}")
    
    
    def estandarizar(self):
        """Estandarización del modelo - CORREGIDA PARA MANEJAR TODOS LOS CASOS"""
        try:
            print("=== ESTANDARIZANDO ===")
            print(f"Restricciones a estandarizar: {self.tipos_restricciones}")
            print(f"Matriz A: {self.A}")
            print(f"Vector b: {self.b}")
            
            # Resetear contadores
            self.variables_holgura = 0
            self.variables_excedente = 0  
            self.variables_artificiales = 0
            
            # Contar variables adicionales necesarias
            for tipo in self.tipos_restricciones:
                if tipo == "<=":
                    self.variables_holgura += 1
                elif tipo == ">=":
                    self.variables_excedente += 1
                    self.variables_artificiales += 1
                elif tipo == "=":
                    self.variables_artificiales += 1
    
            print(f"Variables adicionales: holgura={self.variables_holgura}, excedente={self.variables_excedente}, artificiales={self.variables_artificiales}")
    
            # Verificar términos independientes negativos
            for i, b_val in enumerate(self.b):
                if b_val < 0:
                    print(f"ADVERTENCIA: Término independiente negativo en restricción {i+1}: {b_val}")
                    # Multiplicar la restricción por -1
                    for j in range(len(self.A[i])):
                        self.A[i][j] = -self.A[i][j]
                    self.b[i] = -self.b[i]
                    # Cambiar el tipo de restricción
                    if self.tipos_restricciones[i] == "<=":
                        self.tipos_restricciones[i] = ">="
                    elif self.tipos_restricciones[i] == ">=":
                        self.tipos_restricciones[i] = "<="
                    print(f"Restricción {i+1} corregida: {self.A[i]} {self.tipos_restricciones[i]} {self.b[i]}")
    
            # Crear función objetivo estandarizada
            total_vars = (self.variables_originales + self.variables_holgura + 
                         self.variables_excedente + self.variables_artificiales)
    
            print(f"Total de variables en el modelo estandarizado: {total_vars}")
            
            c_estandarizado = [0.0] * total_vars
    
            # Coeficientes de variables originales
            for i in range(min(self.variables_originales, len(self.c))):
                c_estandarizado[i] = self.c[i]
    
            # Variables de holgura: coeficiente 0
            var_index = self.variables_originales
            for i in range(self.variables_holgura):
                if var_index < total_vars:
                    c_estandarizado[var_index] = 0.0
                    var_index += 1
    
            # Variables de excedente: coeficiente 0
            for i in range(self.variables_excedente):
                if var_index < total_vars:
                    c_estandarizado[var_index] = 0.0
                    var_index += 1
    
            # Variables artificiales: coeficiente M o -M según el tipo
            for i in range(self.variables_artificiales):
                if var_index < total_vars:
                    if self.tipo == "max":
                        c_estandarizado[var_index] = -self.M
                    else:  # min
                        c_estandarizado[var_index] = self.M
                    var_index += 1
    
            # Crear matriz A estandarizada
            A_estandarizada = []
            basic_vars_iniciales = []
    
            # Inicializar matriz con las dimensiones correctas
            for i in range(len(self.A)):
                nueva_restriccion = [0.0] * total_vars
                # Copiar coeficientes originales
                for j in range(min(self.variables_originales, len(self.A[i]))):
                    nueva_restriccion[j] = self.A[i][j]
                A_estandarizada.append(nueva_restriccion)
    
            # Llenar las columnas de variables adicionales
            contador_holgura = 0
            contador_excedente = 0
            contador_artificial = 0
    
            print("=== PROCESANDO RESTRICCIONES ===")
            for i, tipo in enumerate(self.tipos_restricciones):
                print(f"Restricción {i+1}: tipo={tipo}")
                
                if i >= len(A_estandarizada):
                    print(f"ERROR: Índice de restricción {i} fuera de rango")
                    continue
                
                if tipo == "<=":
                    # Variable de holgura
                    col_index = self.variables_originales + contador_holgura
                    if col_index < total_vars:
                        A_estandarizada[i][col_index] = 1.0
                        basic_vars_iniciales.append(col_index)
                        print(f"  Agregada variable de holgura S{contador_holgura+1} en columna {col_index}")
                    contador_holgura += 1
                
                elif tipo == ">=":
                    # Variable de excedente (negativa) y artificial
                    col_excedente = self.variables_originales + self.variables_holgura + contador_excedente
                    col_artificial = (self.variables_originales + self.variables_holgura + 
                                    self.variables_excedente + contador_artificial)
                    
                    if col_excedente < total_vars:
                        A_estandarizada[i][col_excedente] = -1.0  # Variable de excedente
                        print(f"  Agregada variable de excedente -S{self.variables_holgura + contador_excedente + 1} en columna {col_excedente}")
                    
                    if col_artificial < total_vars:
                        A_estandarizada[i][col_artificial] = 1.0   # Variable artificial
                        basic_vars_iniciales.append(col_artificial)
                        print(f"  Agregada variable artificial A{contador_artificial+1} en columna {col_artificial}")
                    
                    contador_excedente += 1
                    contador_artificial += 1
                    
                elif tipo == "=":
                    # Solo variable artificial
                    col_artificial = (self.variables_originales + self.variables_holgura + 
                                    self.variables_excedente + contador_artificial)
                    if col_artificial < total_vars:
                        A_estandarizada[i][col_artificial] = 1.0
                        basic_vars_iniciales.append(col_artificial)
                        print(f"  Agregada variable artificial A{contador_artificial+1} en columna {col_artificial}")
                    contador_artificial += 1
    
            print(f"Variables básicas iniciales: {basic_vars_iniciales}")
            print(f"Número de restricciones: {len(self.A)}")
            print(f"Número de variables básicas: {len(basic_vars_iniciales)}")
            
            # VERIFICACIÓN CRÍTICA: Asegurar que tenemos suficientes variables básicas
            if len(basic_vars_iniciales) < len(self.A):
                print(f"ADVERTENCIA: Faltan variables básicas. Agregando variables artificiales adicionales...")
                
                # Agregar variables artificiales adicionales donde sea necesario
                for i in range(len(self.A)):
                    # Verificar si esta restricción ya tiene una variable básica
                    tiene_basica = False
                    for var_basica in basic_vars_iniciales:
                        if A_estandarizada[i][var_basica] == 1.0:
                            # Verificar que es la única 1 en esa columna
                            es_unica = True
                            for k in range(len(A_estandarizada)):
                                if k != i and A_estandarizada[k][var_basica] != 0:
                                    es_unica = False
                                    break
                            if es_unica:
                                tiene_basica = True
                                break
                    
                    if not tiene_basica:
                        # Agregar variable artificial adicional
                        if total_vars < len(c_estandarizado):
                            # Extender matrices si es necesario
                            for row in A_estandarizada:
                                row.append(0.0)
                            c_estandarizado.append(self.M if self.tipo == "min" else -self.M)
                            total_vars += 1
                        else:
                            # Usar una columna existente
                            nueva_col = len(c_estandarizado)
                            for row in A_estandarizada:
                                row.append(0.0)
                            c_estandarizado.append(self.M if self.tipo == "min" else -self.M)
                            A_estandarizada[i][nueva_col] = 1.0
                            basic_vars_iniciales.append(nueva_col)
                            self.variables_artificiales += 1
                            print(f"  Agregada variable artificial adicional A{self.variables_artificiales} para restricción {i+1}")
    
            # Verificar que ahora tenemos el número correcto de variables básicas
            if len(basic_vars_iniciales) != len(self.A):
                print(f"ERROR CRÍTICO: Aún no coinciden las variables básicas ({len(basic_vars_iniciales)}) con restricciones ({len(self.A)})")
                # Como último recurso, agregar variables artificiales hasta completar
                while len(basic_vars_iniciales) < len(self.A):
                    fila_sin_basica = len(basic_vars_iniciales)
                    nueva_col = len(c_estandarizado)
                    
                    # Extender todas las filas
                    for row in A_estandarizada:
                        row.append(0.0)
                    c_estandarizado.append(self.M if self.tipo == "min" else -self.M)
                    
                    # Asignar la variable artificial a la fila correspondiente
                    A_estandarizada[fila_sin_basica][nueva_col] = 1.0
                    basic_vars_iniciales.append(nueva_col)
                    self.variables_artificiales += 1
                    print(f"  Agregada variable artificial de emergencia A{self.variables_artificiales} para restricción {fila_sin_basica+1}")
    
            # Guardar modelo estandarizado
            self.pasos_solucion.append({
                'tipo': 'estandarizado',
                'titulo': 'Modelo Estandarizado',
                'c': c_estandarizado,
                'A': A_estandarizada,
                'b': self.b,
                'tipos': ['=' for _ in range(len(self.b))],
                'tipo_opt': self.tipo,
                'variables_originales': self.variables_originales,
                'variables_holgura': self.variables_holgura,
                'variables_excedente': self.variables_excedente,
                'variables_artificiales': self.variables_artificiales
            })
    
            # Actualizar el solver
            self.c = c_estandarizado
            self.A = A_estandarizada
            self.basic_vars = basic_vars_iniciales
    
            print(f"Estandarización completada exitosamente.")
            print(f"Total variables finales: {len(self.c)}")
            print(f"Variables básicas finales: {self.basic_vars}")
            print("=== FIN ESTANDARIZACIÓN ===")
    
            return self.crear_tableau_inicial()
    
        except Exception as e:
            print(f"ERROR en estandarizar: {str(e)}")
            print(f"Traceback completo: {traceback.format_exc()}")
            raise ValueError(f"Error al estandarizar: {str(e)}")
    
    def crear_tableau_inicial(self):
        """Crear el tableau inicial del simplex"""
        try:
            print("=== CREANDO TABLEAU INICIAL ===")
            num_restricciones = len(self.A)
            num_variables = len(self.c)
            
            print(f"Dimensiones: {num_restricciones} restricciones, {num_variables} variables")
            print(f"Variables básicas: {self.basic_vars}")
            
            # Verificar dimensiones
            if len(self.basic_vars) != num_restricciones:
                raise ValueError(f"Número de variables básicas ({len(self.basic_vars)}) no coincide con número de restricciones ({num_restricciones})")
            
            # Crear tableau
            self.tableau = np.zeros((num_restricciones + 1, num_variables + 1))
            
            # Llenar restricciones
            for i in range(num_restricciones):
                for j in range(num_variables):
                    self.tableau[i][j] = self.A[i][j]
                self.tableau[i][num_variables] = self.b[i]
            
            # Llenar fila Z (Cj - Zj)
            for j in range(num_variables):
                zj = 0
                for i in range(num_restricciones):
                    cb = self.c[self.basic_vars[i]]
                    zj += cb * self.tableau[i][j]
                self.tableau[num_restricciones][j] = self.c[j] - zj
            
            # Valor Z
            z_value = 0
            for i in range(num_restricciones):
                cb = self.c[self.basic_vars[i]]
                z_value += cb * self.tableau[i][num_variables]
            self.tableau[num_restricciones][num_variables] = z_value
            
            print("Tableau inicial creado exitosamente")
            print(f"Tableau shape: {self.tableau.shape}")
            return True
            
        except Exception as e:
            print(f"ERROR en crear_tableau_inicial: {str(e)}")
            raise ValueError(f"Error al crear tableau inicial: {str(e)}")
    
    def es_optimo(self):
        """Verificar si la solución es óptima"""
        try:
            num_restricciones = len(self.A)
            num_variables = len(self.c)
            
            if self.tipo == "max":
                for j in range(num_variables):
                    if self.tableau[num_restricciones][j] > 1e-10:
                        return False
            else:
                for j in range(num_variables):
                    if self.tableau[num_restricciones][j] < -1e-10:
                        return False
            return True
        except:
            return False
    
    def encontrar_columna_pivote(self):
        """Encontrar la columna pivote"""
        try:
            num_restricciones = len(self.A)
            num_variables = len(self.c)
            
            if self.tipo == "max":
                max_val = -float('inf')
                col_pivote = -1
                
                for j in range(num_variables):
                    valor_cj_zj = self.tableau[num_restricciones][j]
                    if valor_cj_zj > max_val and valor_cj_zj > 1e-10:
                        max_val = valor_cj_zj
                        col_pivote = j
                
                return col_pivote if max_val > 1e-10 else -1
            else:
                min_val = float('inf')
                col_pivote = -1
                
                for j in range(num_variables):
                    valor_cj_zj = self.tableau[num_restricciones][j]
                    if valor_cj_zj < min_val and valor_cj_zj < -1e-10:
                        min_val = valor_cj_zj
                        col_pivote = j
                
                return col_pivote if min_val < -1e-10 else -1
        except:
            return -1
    
    def encontrar_fila_pivote(self, col_pivote):
        """Encontrar la fila pivote usando la prueba del cociente mínimo"""
        try:
            num_restricciones = len(self.A)
            num_variables = len(self.c)

            min_ratio = float('inf')
            fila_pivote = -1

            for i in range(num_restricciones):
                coef = self.tableau[i][col_pivote]
                bi = self.tableau[i][num_variables]

                if coef > 1e-10:  # Solo considerar coeficientes positivos
                    ratio = bi / coef
                    if ratio >= -1e-10 and ratio < min_ratio:
                        min_ratio = ratio
                        fila_pivote = i

            return fila_pivote
        except:
            return -1
    
    def operaciones_fila(self, fila_pivote, col_pivote):
        """Realizar operaciones de fila para el pivoteo"""
        try:
            num_restricciones = len(self.A)
            num_variables = len(self.c)
            
            # Hacer que el elemento pivote sea 1
            pivote = self.tableau[fila_pivote][col_pivote]
            if abs(pivote) < 1e-10:
                raise ValueError("Elemento pivote es cero")
                
            for j in range(num_variables + 1):
                self.tableau[fila_pivote][j] /= pivote
            
            # Hacer ceros en el resto de la columna
            for i in range(num_restricciones + 1):
                if i != fila_pivote:
                    factor = self.tableau[i][col_pivote]
                    for j in range(num_variables + 1):
                        self.tableau[i][j] -= factor * self.tableau[fila_pivote][j]
            
            # Actualizar variable básica
            self.basic_vars[fila_pivote] = col_pivote
            
        except Exception as e:
            raise ValueError(f"Error en operaciones de fila: {str(e)}")
    
    def calcular_zj_y_cj_zj(self):
        """Calcular valores Zj y Cj-Zj para mostrar en el tableau"""
        try:
            num_restricciones = len(self.A)
            num_variables = len(self.c)
            
            zj_values = []
            cj_zj_values = []
            
            # Calcular Zj para cada columna
            for j in range(num_variables):
                zj = 0
                for i in range(num_restricciones):
                    cb = self.c[self.basic_vars[i]]
                    zj += cb * self.tableau[i][j]
                zj_values.append(zj)
                
                # Calcular Cj - Zj
                cj_zj = self.c[j] - zj
                cj_zj_values.append(cj_zj)
            
            # Calcular Zj para la columna de solución (bi)
            zj_bi = 0
            for i in range(num_restricciones):
                cb = self.c[self.basic_vars[i]]
                zj_bi += cb * self.tableau[i][num_variables]
            
            return zj_values, cj_zj_values, zj_bi
            
        except Exception as e:
            print(f"Error en calcular_zj_y_cj_zj: {str(e)}")
            return [], [], 0
    
    
    def obtener_nombre_variable_ordenado(self, index):
        """Obtener el nombre de la variable según su índice"""
        try:
            if index < self.variables_originales:
                if self.es_dual:
                    return f"Y{index + 1}"
                else:
                    return f"X{index + 1}"
        
            # Variables adicionales
            index_adj = index - self.variables_originales
        
            # Variables S (holgura y excedente)
            total_s = self.variables_holgura + self.variables_excedente
            if index_adj < total_s:
                return f"S{index_adj + 1}"
        
            # Variables A (artificiales)
            index_adj -= total_s
            return f"A{index_adj + 1}"
        except Exception as e:
            print(f"Error en obtener_nombre_variable_ordenado: {str(e)}")
            return f"V{index + 1}"
    
    def valor_funcion_contiene_M(self):
        """Verificar si el valor de la función óptima contiene M"""
        try:
            num_restricciones = len(self.A)
            
            for i in range(num_restricciones):
                cb = self.c[self.basic_vars[i]]
                valor_var = self.tableau[i][len(self.c)]
                
                if abs(cb) >= self.M - 1:
                    if valor_var > 1e-10:
                        return True
            
            return False
        except:
            return False
    
    def verificar_no_acotado(self, col_pivote):
        """Verificar si el problema es no acotado"""
        try:
            num_restricciones = len(self.A)
            
            for i in range(num_restricciones):
                if self.tableau[i][col_pivote] > 1e-10:
                    return False
            return True
        except:
            return False
    
    def resolver(self):
        """Resolver el problema usando el método simplex"""
        try:
            print("=== RESOLVIENDO CON SIMPLEX ===")
            self.iteracion = 0
            max_iteraciones = 100
            tableaux = []
            
            # Calcular valores Zj y Cj-Zj para el tableau inicial
            zj_values, cj_zj_values, zj_bi = self.calcular_zj_y_cj_zj()
            
            # Guardar tableau inicial
            tableau_inicial = {
                'iteracion': self.iteracion,
                'tableau': self.convertir_numpy_a_python(self.tableau.copy()),
                'basic_vars': self.basic_vars.copy(),
                'es_optimo': self.es_optimo(),
                'zj_values': zj_values,
                'cj_zj_values': cj_zj_values,
                'zj_bi': zj_bi
            }
            tableaux.append(tableau_inicial)
            
            while not self.es_optimo() and self.iteracion < max_iteraciones:
                self.iteracion += 1
                
                # Encontrar columna pivote
                col_pivote = self.encontrar_columna_pivote()
                if col_pivote == -1:
                    break
                
                # Verificar si es no acotado
                if self.verificar_no_acotado(col_pivote):
                    return {
                        'error': 'Problema no acotado',
                        'pasos_solucion': self.convertir_numpy_a_python(self.pasos_solucion),
                        'tableaux': tableaux,
                        'problema_original': self.problema_original
                    }
                
                # Encontrar fila pivote
                fila_pivote = self.encontrar_fila_pivote(col_pivote)
                if fila_pivote == -1:
                    return {
                        'error': 'Problema no acotado',
                        'pasos_solucion': self.convertir_numpy_a_python(self.pasos_solucion),
                        'tableaux': tableaux,
                        'problema_original': self.problema_original
                    }
                
                # Guardar información de las variables que entran y salen
                var_entrante = self.obtener_nombre_variable_ordenado(col_pivote)
                var_saliente = self.obtener_nombre_variable_ordenado(self.basic_vars[fila_pivote])
                
                # Realizar operaciones de fila
                self.operaciones_fila(fila_pivote, col_pivote)
                
                # Calcular valores Zj y Cj-Zj después del pivoteo
                zj_values, cj_zj_values, zj_bi = self.calcular_zj_y_cj_zj()
                
                # Guardar tableau de esta iteración
                tableau_actual = {
                    'iteracion': self.iteracion,
                    'tableau': self.convertir_numpy_a_python(self.tableau.copy()),
                    'basic_vars': self.basic_vars.copy(),
                    'es_optimo': self.es_optimo(),
                    'col_pivote': col_pivote,
                    'fila_pivote': fila_pivote,
                    'var_entrante': var_entrante,
                    'var_saliente': var_saliente,
                    'zj_values': zj_values,
                    'cj_zj_values': cj_zj_values,
                    'zj_bi': zj_bi
                }
                tableaux.append(tableau_actual)
            
            if self.iteracion >= max_iteraciones:
                return {
                    'error': 'Se alcanzó el máximo número de iteraciones',
                    'pasos_solucion': self.convertir_numpy_a_python(self.pasos_solucion),
                    'tableaux': tableaux,
                    'problema_original': self.problema_original
                }
            
            # Verificar si hay solución factible
            if self.es_optimo() and self.valor_funcion_contiene_M():
                return {
                    'error': 'Problema sin solución factible',
                    'pasos_solucion': self.convertir_numpy_a_python(self.pasos_solucion),
                    'tableaux': tableaux,
                    'problema_original': self.problema_original
                }
            
            return self.obtener_solucion_completa(tableaux)
            
        except Exception as e:
            print(f"ERROR en resolver: {str(e)}")
            return {
                'error': f'Error al resolver: {str(e)}',
                'pasos_solucion': self.convertir_numpy_a_python(self.pasos_solucion) if hasattr(self, 'pasos_solucion') else [],
                'tableaux': [],
                'problema_original': self.problema_original if hasattr(self, 'problema_original') else {}
            }
    
    def obtener_solucion_completa(self, tableaux):
        """Obtener la solución completa con todos los detalles"""
        try:
            num_restricciones = len(self.A)
            num_variables = len(self.c)
        
            # Variables básicas
            variables_basicas = []
            for i in range(num_restricciones):
                var_index = self.basic_vars[i]
                valor = float(self.tableau[i][num_variables])
                var_name = self.obtener_nombre_variable_ordenado(var_index)
                variables_basicas.append({
                    'nombre': var_name,
                    'valor': round(valor, 4)
                })
        
            # Variables no básicas
            variables_no_basicas = []
            for j in range(num_variables):
                if j not in self.basic_vars:
                    var_name = self.obtener_nombre_variable_ordenado(j)
                    variables_no_basicas.append({
                        'nombre': var_name,
                        'valor': 0
                    })
        
            # Valor óptimo de Z
            z_optimo = 0
            for i in range(num_restricciones):
                cb = self.c[self.basic_vars[i]]
                z_optimo += cb * float(self.tableau[i][num_variables])
        
            # Convertir pasos_solucion a tipos Python
            pasos_convertidos = self.convertir_numpy_a_python(self.pasos_solucion)
        
            # Añadir los valores de Cj a cada tableau
            for tableau in tableaux:
                tableau['cj'] = self.convertir_numpy_a_python(self.c)
        
            resultado = {
                'exito': True,
                'variables_basicas': variables_basicas,
                'variables_no_basicas': variables_no_basicas,
                'z_optimo': round(float(z_optimo), 4),
                'tipo_optimizacion': self.tipo,
                'tableaux': tableaux,
                'pasos_solucion': pasos_convertidos,
                'es_dual': self.es_dual,
                'variables_originales': self.variables_originales,
                'variables_holgura': self.variables_holgura,
                'variables_excedente': self.variables_excedente,
                'variables_artificiales': self.variables_artificiales,
                'problema_original': self.problema_original
            }
        
            return resultado
        
        except Exception as e:
            print(f"ERROR en obtener_solucion_completa: {str(e)}")
            return {
                'error': f'Error al obtener solución: {str(e)}',
                'pasos_solucion': self.convertir_numpy_a_python(self.pasos_solucion) if hasattr(self, 'pasos_solucion') else [],
                'tableaux': [],
                'problema_original': self.problema_original if hasattr(self, 'problema_original') else {}
            }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/resolver', methods=['POST'])
def resolver_problema():
    try:
        print("\n" + "="*60)
        print("NUEVA PETICIÓN A /resolver")
        print("="*60)
        
        if not request.is_json:
            return jsonify({'error': 'La petición debe ser JSON'}), 400
            
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No se recibieron datos'}), 400
            
        if 'funcion_objetivo' not in data:
            return jsonify({'error': 'Falta la función objetivo'}), 400
            
        if 'tipo_optimizacion' not in data:
            return jsonify({'error': 'Falta el tipo de optimización'}), 400
            
        if 'restricciones' not in data:
            return jsonify({'error': 'Faltan las restricciones'}), 400
        
        # Filtrar restricciones vacías
        restricciones = [r.strip() for r in data['restricciones'] if r.strip()]
        
        if not restricciones:
            return jsonify({'error': 'Debe proporcionar al menos una restricción'}), 400
        
        solver = SimplexSolver()
        
        try:
            # Configurar el problema
            solver.configurar_problema(
                data['funcion_objetivo'].strip(),
                data['tipo_optimizacion'],
                restricciones
            )
            
            # Aplicar dualidad si se solicita
            if data.get('aplicar_dualidad', False):
                solver.aplicar_dualidad()
            
            # Estandarizar
            if not solver.estandarizar():
                return jsonify({
                    'error': 'Error al estandarizar el problema',
                    'pasos_solucion': solver.convertir_numpy_a_python(solver.pasos_solucion),
                    'problema_original': solver.problema_original
                }), 400
            
            # Resolver
            resultado = solver.resolver()
            
            if 'error' in resultado:
                return jsonify(resultado), 400
            
            return jsonify(resultado)
            
        except Exception as solver_error:
            return jsonify({
                'error': str(solver_error),
                'pasos_solucion': solver.convertir_numpy_a_python(solver.pasos_solucion) if hasattr(solver, 'pasos_solucion') else [],
                'problema_original': solver.problema_original if hasattr(solver, 'problema_original') else {}
            }), 400
        
    except Exception as e:
        print(f"Error inesperado: {str(e)}")
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
