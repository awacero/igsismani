from scipy.interpolate import interp1d
import numpy as np

# Define los colores y los valores correspondientes de intensidad
shakemap_values = np.linspace(1, 10, 10)  # Ahora va de 1 a 10
shakemap_colors = [
    'rgb(128,128,255)', 'rgb(191,204,255)', 'rgb(160,230,255)', 'rgb(128,255,255)',
    'rgb(122,255,147)', 'rgb(255,255,0)', 'rgb(255,200,0)', 'rgb(255,145,0)',
    'rgb(255,0,0)', 'rgb(200,0,0)'
]

# Separa los componentes RGB para cada color
shakemap_rgb = [tuple(map(int, color[4:-1].split(','))) for color in shakemap_colors]

# Crea funciones de interpolación para cada componente de color
interp_r = interp1d(shakemap_values, [color[0] for color in shakemap_rgb])
interp_g = interp1d(shakemap_values, [color[1] for color in shakemap_rgb])
interp_b = interp1d(shakemap_values, [color[2] for color in shakemap_rgb])

def get_colors_from_intensity(intensity):
    # Limita la intensidad al rango [1, 10]
    intensity = np.clip(intensity, 1, 10)
    
    # Interpola los componentes de color
    r = int(interp_r(intensity))
    g = int(interp_g(intensity))
    b = int(interp_b(intensity))
    
    # Genera 3 tonalidades para cada color
    colors = []
    for factor in [0.8, 1.0, 1.2]:
        r_tone = int(np.clip(r * factor, 0, 255))
        g_tone = int(np.clip(g * factor, 0, 255))
        b_tone = int(np.clip(b * factor, 0, 255))
        
        colors.append(f'rgb({r_tone},{g_tone},{b_tone})')
    
    return colors


def get_color_from_intensity(intensity):
    # Limita la intensidad al rango [1, 10]
    intensity = np.clip(intensity, 1, 10)
    
    # Calcula los componentes interpolados
    r = int(interp_r(intensity))
    g = int(interp_g(intensity))
    b = int(interp_b(intensity))
    
    return f'rgb({r},{g},{b})'


def get_value_from_intensity(intensity):
    """
    Interpola la intensidad en el rango [1, 10] hacia un valor en el rango [0.1, 0.3].
    """
    intensity = np.clip(intensity, 1, 10)  # Asegura que esté en el rango permitido
    return np.interp(intensity, [1, 10], [0.5, 1])