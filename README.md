# HMI_YOLO_311D_FSAB

Esqueleto funcional de una aplicacion industrial de vision artificial. Esta primera
etapa ofrece una HMI sencilla y un PLC completamente simulado; no se conecta a
hardware ni a una red industrial.

## Estado actual

- Ventana PySide6 con estado del PLC, controles y eventos.
- `HmiService` y `PlcService` independientes de la interfaz.
- Cliente PLC simulado con lectura y escritura en memoria.
- Operaciones de conexion en un hilo Qt para no bloquear la HMI.
- Configuracion INI, variables de entorno y logging centralizado.
- Pruebas unitarias y de integracion sin hardware ni pantalla visible.
- Camara simulada con patron RGB animado y vista previa en la HMI.
- Captura USB real mediante OpenCV/DirectShow, validada con Arducam IMX477 HQ.
- Inferencia simulada con deteccion, caja, clase, confianza y tiempo de proceso.
- Inspeccion manual OK/NOK con reglas configurables y contadores en memoria.
- Navegacion modular para Operacion, Monitor I/O, Eventos, Configuracion y Mantenimiento.
- Temas oscuro, claro y alto contraste con animaciones opcionales.
- Alarmas de sesion con severidad, filtros, contador y reconocimiento.
- Supervision de salud con heartbeats, timeouts y recuperacion de estado.
- Candado de inspeccion: ninguna inspeccion se ejecuta sin conexion al PLC.
- Historial local compacto en JSONL con retencion automatica de siete dias.
- Pantalla de historial con filtros, uso de espacio, exportacion CSV y limpieza confirmada.
- Adaptador preparado para Omron Sysmac NX mediante EtherNet/IP explicito.
- Monitor configurable de 10 entradas y 10 salidas booleanas, mensaje STRING y porcentaje.
- Indicadores circulares negro/verde brillante para E/S booleanas, con ambar y rojo para
  transiciones y fallos de PLC/camara.
- Pantalla de operacion ordenada por etapas: preparar equipos, verificar imagen e inspeccionar.
- Monitor I/O orientado al operador, con jerarquia visual, filas alternadas y direccion por color.

## Requisitos

- Python 3.10 estable de 64 bits (`>=3.10,<3.11`).
- Windows durante el desarrollo inicial.

PySide6 6.7.3 se fija porque admite Python 3.10 y ofrece ruedas para Windows
x86-64 y Linux ARM64 con glibc 2.31. La compatibilidad final se debe comprobar
contra las versiones exactas de JetPack y L4T.

## Instalacion en Windows

Desde `proyecto2`:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
python -c "import sys; print(sys.executable)"
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

El primer comando de comprobacion debe indicar Python 3.10 y el segundo debe
apuntar a `proyecto2\.venv`.

## Uso y verificaciones

```powershell
python -m hmi_yolo_311d_fsab
pytest -v
mypy src --strict
ruff check .
ruff format --check .
```

## Arquitectura

- `app`: composition root y ciclo de vida de Qt y servicios.
- `domain`: estados, errores, valores y contrato del cliente PLC.
- `services`: coordinacion de PLC y estado apropiado para la HMI.
- `infrastructure`: configuracion, logging y simulador concreto.
- `presentation`: ventana y worker de concurrencia Qt.
- `tests`: pruebas unitarias y de integracion.

La ventana nunca accede al cliente PLC. Sus acciones llegan al `HmiService` por
un worker Qt; este coordina al `PlcService`, que usa el contrato `PlcClient`.
La camara sigue el mismo limite arquitectonico mediante `CameraService` y
`CameraClient`; la captura se ejecuta en el hilo de servicios.

La interfaz usa una barra lateral. **Operacion** concentra video y ciclo;
**Monitor I/O** presenta señales; **Eventos** conserva mensajes de la sesion;
**Configuracion** abre los parametros editables; y **Mantenimiento** muestra
versiones y el estado de integración actual.

La seccion **Alarmas** recibe errores controlados de PLC y camara, permite
filtrar y reconocer eventos y muestra su cantidad activa en la navegacion. Las
alarmas viven en memoria durante esta etapa; el detalle tecnico permanece en el
log.

La pestaña **Apariencia** permite cambiar inmediatamente entre tema oscuro,
claro y alto contraste, y desactivar transiciones mediante **Reducir
animaciones**. La preferencia queda guardada en `runtime.ini`.

## Salud y diagnostico

`HealthService` supervisa PLC, camara e inferencia. Los frames renuevan los
heartbeats de adquisicion y procesamiento; un timeout cambia el componente a
`UNAVAILABLE` y genera una unica alarma hasta su recuperacion. Mantenimiento
muestra estado, detalle y ultimo heartbeat. Los componentes detenidos
intencionalmente no producen falsas alarmas.

## Camara simulada

Los botones **Iniciar camara** y **Detener camara** controlan un generador de
frames RGB determinista. El visor permite comprobar el flujo de captura y la
responsividad de la HMI sin camara fisica ni OpenCV. Resolucion y velocidad se
configuran en los archivos INI o con `HMI_YOLO_CAMERA_WIDTH`,
`HMI_YOLO_CAMERA_HEIGHT` y `HMI_YOLO_CAMERA_FPS`.

La configuracion de camara contempla los backends `simulated`, `v4l2` y
`argus`, puerto `/dev/videoN`, `sensor-id`, perfil de captura, formato de pixel,
buffers, rotacion, volteo, timeout, reconexion y fallback. **Buscar camaras**
enumera nodos V4L2 disponibles. En un equipo sin camara muestra un resultado
vacio y conserva el simulador.

La captura V4L2/Argus permanece bloqueada hasta conectar una camara y validar
modelo, controlador y JetPack/L4T. Si se desactiva el fallback, seleccionar un
backend real produce un error claro en lugar de simular silenciosamente.

## Camara USB con OpenCV

En Windows, el backend `opencv` abre dispositivos UVC por indice mediante DirectShow.
El boton **Buscar camaras** muestra los dispositivos multimedia detectados y su indice.
Instale el soporte opcional con `python -m pip install -e ".[camera]"`. La Arducam
IMX477 HQ USB fue validada en el indice `0` a 640x480; esta captura es real, aunque la
inferencia continua simulada hasta integrar el modelo YOLO.

## Inferencia simulada

Cada frame pasa por `InferenceService` y un motor determinista genera una
deteccion de clase `pieza`. La HMI dibuja su caja y presenta confianza, cantidad
de objetos y tiempo de proceso. Puede configurarse con
`HMI_YOLO_INFERENCE_ENABLED` y `HMI_YOLO_CONFIDENCE_THRESHOLD`.

Este motor valida el flujo de datos, la concurrencia y la presentacion; no es un
modelo de vision y no toma decisiones industriales reales.

## Capturas para dataset

Con la camara activa, **Capturar** almacena el ultimo frame RGB original en
`data/captures`. El PNG no contiene la caja ni el texto de la inferencia simulada, por
lo que puede revisarse y clasificarse posteriormente para construir el dataset. Las
capturas son manuales y no tienen retencion automatica; deben respaldarse antes de
limpiar el directorio de datos.

## Inspeccion OK/NOK

Con la camara iniciada y el PLC conectado, **Ejecutar inspeccion** evalua las
detecciones del ultimo frame. El boton permanece bloqueado si falta cualquiera
de esas condiciones y el servicio vuelve a validar la conexion para impedir que
otra ruta omita el candado. Las reglas definen clase, confianza y rango de objetos. La HMI
muestra el resultado, motivo y contadores; **Reiniciar contadores** los devuelve
a cero. Los valores pueden sobrescribirse con `HMI_YOLO_EXPECTED_LABEL`,
`HMI_YOLO_INSPECTION_CONFIDENCE`, `HMI_YOLO_MINIMUM_OBJECTS` y
`HMI_YOLO_MAXIMUM_OBJECTS`.

Cada resultado se agrega a `data/inspections/inspections-AAAA-MM-DD.jsonl`.
Solo se guardan metadatos compactos, nunca frames; al escribir o arrancar se
eliminan archivos fuera de la ventana de siete dias. No se utiliza una base de
datos ni se agregan dependencias.

La seccion **Historial** muestra los resultados mas recientes, permite filtrar
por fecha y estado OK/NOK, exportar solo las filas visibles a CSV y consultar el
espacio ocupado. **Limpiar historial** exige confirmacion antes de eliminar los
archivos administrados por la aplicacion.

## Configuracion operativa e I/O

El boton **Configuracion** permite editar conexion PLC, camara, inferencia,
reglas de inspeccion y mapeo de tags. Los cambios se validan y se guardan de
forma atomica en `config/runtime.ini`; se aplican en el siguiente arranque.

El monitor de entradas y salidas presenta nombre logico, tag, tipo, direccion,
valor y calidad. Las salidas solo son editables manualmente mientras se utiliza
el PLC simulado. El modo real continua bloqueado hasta implementar el adaptador
y definir las reglas de seguridad para escritura.

## Ciclo automatico simulado

Al conectar el PLC e iniciar la camara, **Simular trigger PLC** ejecuta un ciclo
completo. El handshake actualiza `inspection_busy`, `inspection_complete`,
`inspection_ok`, `inspection_nok` e `inspection_sequence`. **Reconocer resultado**
limpia las salidas de resultado y prepara el siguiente disparo. Este flujo solo
opera contra el cliente PLC simulado.

## PLC simulado

Inicia desconectado y mantiene variables en memoria. Rechaza lecturas y
escrituras sin conexion, informa variables inexistentes y puede simular un fallo
de conexion con:

```powershell
$env:HMI_YOLO_SIMULATE_CONNECTION_ERROR = "true"
python -m hmi_yolo_311d_fsab
```

Otras variables disponibles son `HMI_YOLO_ENV`, `HMI_YOLO_PLC_MODE`,
`HMI_YOLO_PLC_HOST`, `HMI_YOLO_PLC_PORT`, `HMI_YOLO_PLC_TIMEOUT_SECONDS`,
`HMI_YOLO_PLC_RECONNECT_SECONDS`, `HMI_YOLO_LOG_LEVEL`, `HMI_YOLO_CONFIG_DIR`,
`HMI_YOLO_LOG_DIR` y `HMI_YOLO_DATA_DIR`.

## Omron Sysmac NX por EtherNet/IP

El modo `real` utiliza mensajes explicitos y nombres simbolicos mediante APHYT.
La IP, puerto, timeout, intervalo de reconexion y todos los tags se editan en la
HMI. El puerto predeterminado es TCP 44818; un valor no compatible se rechaza de
forma controlada. Para instalar el adaptador opcional:

```powershell
python -m pip install -e ".[plc]"
```

La configuracion inicial contiene 10 entradas BOOL y 10 salidas BOOL, ademas de
`operator_message` (STRING), `inspection_sequence` (INT) y `quality_percent`
(REAL). Los nombres son provisionales y deben reemplazarse por los publicados en
Sysmac Studio. Ante una perdida de comunicacion se detiene el sondeo, se bloquea
la inspeccion y aparece una ventana con las opciones **Reintentar** y **Cancelar**.
El banner superior refleja el contenido de `operator_message`.

El porcentaje escrito en `quality_percent` corresponde por ahora a la confianza
mas alta del frame. El criterio y tiempo del ciclo se ajustaran con mediciones
reales cuando esten disponibles el PLC, la camara y la pieza.

## Etapa visual con fotografias

Cuando se reciba el paquete de fotografias se clasificaran logotipos, fondos,
productos y estados; se optimizaran para la Jetson y se integraran como recursos
de la aplicacion. Se conservaran variantes legibles para los temas oscuro, claro
y alto contraste. Esta etapa no bloquea la logica industrial actual.

## Limitaciones y siguientes etapas

No se incluyen camara real, YOLO, PyTorch, CUDA, TensorRT, persistencia historica
de largo plazo ni logica de produccion validada. El adaptador Omron debe probarse
con el modelo exacto, firmware, tags publicados y red industrial antes de usarse
en produccion.

Docker se pospone hasta conocer JetPack/L4T, CUDA/TensorRT, camara, visualizacion
de la HMI y acceso a dispositivos. Esto evita elegir una imagen o configuracion
incompatible con la NVIDIA Jetson Orin Nano.

