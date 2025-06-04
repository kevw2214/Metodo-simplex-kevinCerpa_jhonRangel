# Método Simplex - Interfaz Web

Una aplicación web moderna para resolver problemas de programación lineal usando el método Simplex, desarrollada con Flask y Bootstrap.

## Características

- **Método Simplex Completo**: Implementación completa del algoritmo Simplex con visualización paso a paso
- **Aplicación de Dualidad**: Conversión automática a problema dual con explicación detallada
- **Estandarización Automática**: Conversión a forma estándar con variables de holgura y artificiales
- **Interfaz Moderna**: Diseño responsivo con Bootstrap 5
- **Visualización de Tableaux**: Muestra todos los tableaux generados durante el proceso
- **Ejemplos Incluidos**: Ejemplos predefinidos para facilitar el aprendizaje

## Instalación

1. Clona o descarga el proyecto
2. Instala las dependencias:
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`
3. Ejecuta la aplicación:
   \`\`\`bash
   python app.py
   \`\`\`
4. Abre tu navegador en `http://localhost:5000`

## Uso

1. **Configurar el Problema**:
   - Selecciona si deseas maximizar o minimizar
   - Ingresa la función objetivo (ej: `2x1 + 3x2`)
   - Agrega las restricciones (ej: `x1 + x2 <= 4`)

2. **Opciones Avanzadas**:
   - Marca "Aplicar Dualidad" si deseas resolver el problema dual

3. **Resolver**:
   - Haz clic en "Resolver Problema"
   - Revisa la solución paso a paso

## Formato de Entrada

### Función Objetivo
- `2x1 + 3x2` - Coeficientes positivos
- `2x1 - 3x2` - Coeficientes negativos  
- `x1 + x2` - Coeficiente 1 implícito

### Restricciones
- `2x1 + 3x2 <= 100` - Menor o igual
- `x1 + x2 >= 50` - Mayor o igual
- `2x1 = 80` - Igualdad

## Tecnologías Utilizadas

- **Backend**: Flask (Python)
- **Frontend**: Bootstrap 5, JavaScript
- **Cálculos**: NumPy
- **Iconos**: Font Awesome

## Estructura del Proyecto

\`\`\`
├── app.py              # Aplicación Flask principal
├── templates/
│   ├── base.html       # Template base
│   └── index.html      # Página principal
├── requirements.txt    # Dependencias
└── README.md          # Este archivo
\`\`\`

## Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo LICENSE para más detalles.
