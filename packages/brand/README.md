# @deken/brand

Tokens de la identidad visual de Grupo Deken para la interfaz y, más adelante, para las
plantillas de render.

Fuente de los valores: guía de marca de DEKEN (skill `estilo-de-marca`), medidos sobre
los logos reales. **No se improvisan colores.**

- Dos colores de marca: verde `#76B82A` (acento único) y gris `#383E42`.
- Neutros derivados del gris (tono 204°, saturación 8,2 %).
- **Prohibido texto blanco sobre verde** (2,42:1). Sobre verde, `#0D0E0F` (7,97:1).
- Montserrat (marca) e IBM Plex Mono (datos técnicos y etiquetas). Sin cursiva.
- En vídeo 1080×1920: nada por debajo de 30 px; el logo no aparece antes del segundo 3.

`src/palette.test.ts` comprueba automáticamente los contrastes WCAG AA de todos los
pares texto/fondo de ambos temas y la prohibición de blanco sobre verde.

Los logos oficiales no se incluyen en el repositorio: se subirán desde *Marca DEKEN*
(Sprint 1), que mide su color real en lugar de fiarse del nombre del fichero.
