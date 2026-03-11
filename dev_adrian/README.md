# dev_adrian Workspace Notes

## Contexto
Este workspace toma **Layer 1** (`software/layer1_radar`) como referencia existente para adquisición UART y parseo TLV.

## Estado actual
Las capas **Layer 2 a Layer 8** ya incluyen una base funcional mínima, tipada y conectable entre sí:
- No hay placeholders vacíos.
- Cada capa expone contratos públicos (`__init__.py` + `__all__`).
- Implementación ligera y determinística, apta para smoke tests end-to-end.

## Alcance
La implementación evita lógica de hardware real y dependencias pesadas, pero mantiene estructura extensible para evolución a producción.
