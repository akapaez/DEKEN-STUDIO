# ADR 0004 — FFmpeg como motor de render de V1; Remotion opcional

- Estado: **sustituida** por [ADR 0005](0005-remotion-composition-engine.md) (Sprint 1).
  FFmpeg sigue siendo el motor de análisis, proxys y verificación; el render final y
  la composición pasan a Remotion, con puerta de licencia.

## Contexto
La brief propone FFmpeg y Remotion. La licencia de Remotion exige *Company License* para
empresas de más de 3 empleados.

## Decisión
- V1 renderiza la línea de tiempo con FFmpeg (`filter_complex` generado): recortes,
  reencuadre sin deformar, subtítulos con libass, mezcla de audio, H.264/AAC.
- Remotion queda como motor opcional para piezas gráficas, desactivado hasta que DEKEN
  confirme la licencia. Su salida (ProRes 4444 con alfa) entraría en la timeline como un
  clip más.

## Consecuencias
Sin dependencia de licencia para el recorrido fundamental. Las animaciones de marca
avanzadas dependen de la decisión de licencia.
