import c4d

# Здесь можно хранить все константы плагина.

# !!! ОБЯЗАТЕЛЬНО !!!
# Поставь сюда свой уникальный ID из PluginCafe,
# если будешь использовать плагин всерьёз или распространять его.
PLUGIN_ID: int = 1244567

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
DEFAULT_SHAKE_POS: float = 5.0
DEFAULT_SHAKE_ROT: float = 1.0
DEFAULT_TARGET_BLEND: float = 0.0
DEFAULT_SHAKE_ENABLE: bool = False
DEFAULT_USE_TARGET_B: bool = True

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
UD_SHAKE_ENABLE = "Shake Enable"
UD_SHAKE_POS = "Shake Pos"
UD_SHAKE_ROT = "Shake Rot"
UD_TARGET_A = "Target A"
UD_TARGET_B = "Target B"
UD_USE_TARGET_B = "Use Target B"
UD_TARGET_BLEND = "Target Blend"

# Имена объектов рига (для создания и поиска по имени)
RIG_ROOT_NAME: str = "Cam_Rig"
MAIN_CAMERA_NAME: str = "Main_Camera"
TARGET_A_NAME: str = "Target_A"
TARGET_B_NAME: str = "Target_B"
LOOK_TARGET_NAME: str = "Look_Target"
FOLLOW_NAME: str = "Follow"
OFFSET_NAME: str = "Offset"

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
    UD_SHAKE_ENABLE: DEFAULT_SHAKE_ENABLE,
    UD_SHAKE_POS: DEFAULT_SHAKE_POS,
    UD_SHAKE_ROT: DEFAULT_SHAKE_ROT,
    UD_USE_TARGET_B: DEFAULT_USE_TARGET_B,
    UD_TARGET_BLEND: DEFAULT_TARGET_BLEND,
}
