import c4d

# Здесь можно хранить все константы плагина.

# !!! ОБЯЗАТЕЛЬНО !!!
# Поставь сюда свой уникальный ID из PluginCafe,
# если будешь использовать плагин всерьёз или распространять его.
PLUGIN_ID: int = 1244567
# ID тега-маркера рига (для поиска ригов по тегу, опционально)
PLUGIN_ID_RIG_TAG: int = 1244570
# ID ObjectData CamRigRoot (null с иконкой камеры)
PLUGIN_ID_CAMRIG_ROOT: int = 1244571

# Focus object display: форма, радиус, цвет (null под FX_CAM)
FOCUS_DISPLAY_RADIUS: float = 30.0
FOCUS_COLOR: object = c4d.Vector(1, 1, 0)
# NULLOBJECT_DISPLAY: 0=Dot, 1=Point, 2=Circle, 3=Rectangle, 4=Sphere
FOCUS_DISPLAY_MODE: int = 4
# ID_BASEOBJECT_USECOLOR: 2 = Always (иначе цвет игнорируется)
FOCUS_USECOLOR_MODE: int = 2

PLUGIN_VERSION: str = "1.1"
PLUGIN_NAME: str = "Cam Rig Builder"
PLUGIN_HELP: str = "Create camera rig"

# Дефолтные значения для рига (используются при создании и при Reset)
DEFAULT_ORBIT: float = 0.0
DEFAULT_RADIUS: float = 500.0
DEFAULT_OFFSET_X: float = 0.0
DEFAULT_OFFSET_Y: float = 0.0
DEFAULT_OFFSET_Z: float = 0.0
DEFAULT_ROT_H: float = 0.0
DEFAULT_ROT_P: float = 0.0
DEFAULT_ROT_B: float = 0.0
DEFAULT_FOCAL: float = 36.0
DEFAULT_FOCUS_DISTANCE: float = 1000.0
DEFAULT_SHAKE_POS: float = 5.0
DEFAULT_SHAKE_ROT: float = 1.0
DEFAULT_TARGET_BLEND: float = 0.0
DEFAULT_SHAKE_ENABLE: bool = False
DEFAULT_USE_TARGET: bool = True
DEFAULT_FREE_CAMERA: bool = False

# User Data имена
UD_ORBIT = "Orbit"
UD_RADIUS = "Radius"
UD_OFFSET_X = "Offset X"
UD_OFFSET_Y = "Offset Y"
UD_OFFSET_Z = "Offset Z"
UD_ROT_H = "Rot H"
UD_ROT_P = "Rot P"
UD_ROT_B = "Rot B"
UD_FOCAL = "Focal Length"
UD_FOCUS_DISTANCE: str = "Focus Distance"
UD_SHAKE_ENABLE = "Shake Enable"
UD_SHAKE_POS = "Shake Pos"
UD_SHAKE_ROT = "Shake Rot"
UD_TARGET_A = "Target A"
UD_TARGET_B = "Target B"
UD_USE_TARGET = "Use Target"
UD_TARGET_BLEND = "Target Blend"
UD_FREE_CAMERA = "Free Camera"

# Имена объектов рига (шаблоны; с суффиксом: Cam_Rig_0, Main_Camera_0, ...)
RIG_ROOT_NAME: str = "Cam_Rig"
MAIN_CAMERA_NAME: str = "Main_Camera"

# Группы для адресного сброса: имя группы -> ключи UD (один источник имён — UD_*)
RESET_GROUP_KEYS: dict = {
    "orbit": [UD_ORBIT, UD_RADIUS],
    "offset": [UD_OFFSET_X, UD_OFFSET_Y, UD_OFFSET_Z],
    "rotation": [UD_ROT_H, UD_ROT_P, UD_ROT_B],
    "transform": [UD_OFFSET_X, UD_OFFSET_Y, UD_OFFSET_Z, UD_ROT_H, UD_ROT_P, UD_ROT_B],
    "camera": [UD_FOCAL, UD_FOCUS_DISTANCE],
    "target": [UD_USE_TARGET, UD_TARGET_BLEND, UD_FREE_CAMERA],
    "shake": [UD_SHAKE_ENABLE, UD_SHAKE_POS, UD_SHAKE_ROT],
}
TARGET_A_NAME: str = "Target_A"
TARGET_B_NAME: str = "Target_B"
LOOK_TARGET_NAME: str = "Look_Target"
FOLLOW_NAME: str = "Follow"
OFFSET_NAME: str = "Offset"
FOCUS_NAME: str = "Focus"

# Системный слой для служебных объектов всех ригов (один на документ)
SYSTEM_LAYER_NAME: str = "hidenSysRig"

# Redshift Camera type ID (fallback to Ocamera if Redshift not available)
RS_CAMERA_ID: int = 1057516

# Дефолты User Data для сброса (только REAL и BOOL; Link не сбрасываем)
UD_DEFAULTS: dict = {
    UD_ORBIT: DEFAULT_ORBIT,
    UD_RADIUS: DEFAULT_RADIUS,
    UD_OFFSET_X: DEFAULT_OFFSET_X,
    UD_OFFSET_Y: DEFAULT_OFFSET_Y,
    UD_OFFSET_Z: DEFAULT_OFFSET_Z,
    UD_ROT_H: DEFAULT_ROT_H,
    UD_ROT_P: DEFAULT_ROT_P,
    UD_ROT_B: DEFAULT_ROT_B,
    UD_FOCAL: DEFAULT_FOCAL,
    UD_FOCUS_DISTANCE: DEFAULT_FOCUS_DISTANCE,
    UD_SHAKE_ENABLE: DEFAULT_SHAKE_ENABLE,
    UD_SHAKE_POS: DEFAULT_SHAKE_POS,
    UD_SHAKE_ROT: DEFAULT_SHAKE_ROT,
    UD_USE_TARGET: DEFAULT_USE_TARGET,
    UD_TARGET_BLEND: DEFAULT_TARGET_BLEND,
    UD_FREE_CAMERA: DEFAULT_FREE_CAMERA,
}
