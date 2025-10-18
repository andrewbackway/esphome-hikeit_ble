import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.components import ble_client, select, number, switch, button, text_sensor
from esphome.const import (
    CONF_ID,
    CONF_MAC_ADDRESS,
    CONF_NAME,
    CONF_TRIGGER_ID,
    DEVICE_CLASS_EMPTY,
)

ICON_SPEEDOMETER = "mdi:speedometer"
ICON_TUNE = "mdi:tune"
ICON_LOCK = "mdi:lock"
ICON_MONITOR = "mdi:monitor"
ICON_CAR = "mdi:car"

DEPENDENCIES = ["ble_client"]
CODEOWNERS = ["@andrewbackway"]
AUTO_LOAD = ["select", "number", "switch", "button", "text_sensor"]

# Component namespace
hikeit_ble_ns = cg.esphome_ns.namespace("hikeit_ble")

# Main component class
HikeITBLEComponent = hikeit_ble_ns.class_(
    "HikeITBLEComponent", 
    cg.Component,
    ble_client.BLEClientNode
)

# Entity classes
HikeITSpeedSelect = hikeit_ble_ns.class_(
    "HikeITSpeedSelect",
    select.Select,
    cg.Component
)

HikeITStepNumber = hikeit_ble_ns.class_(
    "HikeITStepNumber",
    number.Number,
    cg.Component
)

HikeITLockedSwitch = hikeit_ble_ns.class_(
    "HikeITLockedSwitch",
    switch.Switch,
    cg.Component
)

HikeITButton = hikeit_ble_ns.class_(
    "HikeITButton",
    button.Button,
    cg.Component
)

HikeITStatusSensor = hikeit_ble_ns.class_(
    "HikeITStatusSensor",
    text_sensor.TextSensor,
    cg.Component
)

# Triggers
ConnectedTrigger = hikeit_ble_ns.class_(
    "ConnectedTrigger",
    automation.Trigger.template()
)

DisconnectedTrigger = hikeit_ble_ns.class_(
    "DisconnectedTrigger",
    automation.Trigger.template()
)

VerifiedTrigger = hikeit_ble_ns.class_(
    "VerifiedTrigger",
    automation.Trigger.template()
)

MessageReceivedTrigger = hikeit_ble_ns.class_(
    "MessageReceivedTrigger",
    automation.Trigger.template(cg.std_string)
)

# Config keys
CONF_HIKEIT_BLE_ID = "hikeit_ble_id"
CONF_PIN = "pin"
CONF_SPEED_MODEL = "speed_model"
CONF_STEP_ADJUSTMENT = "step_adjustment"
CONF_LOCKED = "locked"
CONF_SCREEN_COMMAND = "screen_command"
CONF_AUTO_COMMAND = "auto_command"
CONF_STATUS = "status"
CONF_ON_CONNECTED = "on_connected"
CONF_ON_DISCONNECTED = "on_disconnected"
CONF_ON_VERIFIED = "on_verified"
CONF_ON_MESSAGE = "on_message"

# Speed model options
SPEED_MODELS = [
    "Economy",
    "Normal",
    "Cruise",
    "Sport",
    "Hike IT",
    "Auto",
    "Launch",
    "Anti-Slip",
    "Valet",
    "SL"
]

# Component configuration schema
CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(HikeITBLEComponent),
            cv.Required(CONF_MAC_ADDRESS): cv.mac_address,
            cv.Optional(CONF_PIN, default="123"): cv.string,
            
            # Entity configs
            cv.Optional(CONF_SPEED_MODEL): select.select_schema(
                HikeITSpeedSelect,
                icon=ICON_SPEEDOMETER,
            ),
            cv.Optional(CONF_STEP_ADJUSTMENT): number.number_schema(
                HikeITStepNumber,
                icon=ICON_TUNE,
            ),
            cv.Optional(CONF_LOCKED): switch.switch_schema(
                HikeITLockedSwitch,
                icon=ICON_LOCK,
                device_class=DEVICE_CLASS_EMPTY,
            ),
            cv.Optional(CONF_SCREEN_COMMAND): button.button_schema(
                HikeITButton,
                icon=ICON_MONITOR,
            ),
            cv.Optional(CONF_AUTO_COMMAND): button.button_schema(
                HikeITButton,
                icon=ICON_CAR,
            ),
            cv.Optional(CONF_STATUS): text_sensor.text_sensor_schema(
                HikeITStatusSensor,
            ),
            
            # Automation triggers
            cv.Optional(CONF_ON_CONNECTED): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(ConnectedTrigger),
                }
            ),
            cv.Optional(CONF_ON_DISCONNECTED): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(DisconnectedTrigger),
                }
            ),
            cv.Optional(CONF_ON_VERIFIED): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(VerifiedTrigger),
                }
            ),
            cv.Optional(CONF_ON_MESSAGE): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(MessageReceivedTrigger),
                }
            ),
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(ble_client.BLE_CLIENT_SCHEMA)
)


async def to_code(config):
    """Generate C++ code for the component."""
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await ble_client.register_ble_node(var, config)
    
    # Set MAC address
    mac = str(config[CONF_MAC_ADDRESS]).replace(":", "")
    mac_bytes = [int(mac[i:i+2], 16) for i in range(0, 12, 2)]
    cg.add(var.set_address(mac_bytes))
    
    # Set PIN
    cg.add(var.set_pin(config[CONF_PIN]))
    
    # Register entities
    if CONF_SPEED_MODEL in config:
        conf = config[CONF_SPEED_MODEL]
        sens = cg.new_Pvariable(conf[CONF_ID])
        await select.register_select(sens, conf, options=SPEED_MODELS)
        cg.add(sens.set_parent(var))
        cg.add(var.set_speed_select(sens))
    
    if CONF_STEP_ADJUSTMENT in config:
        conf = config[CONF_STEP_ADJUSTMENT]
        sens = cg.new_Pvariable(conf[CONF_ID])
        await number.register_number(sens, conf, min_value=0, max_value=15, step=1)
        cg.add(sens.set_parent(var))
        cg.add(var.set_step_number(sens))
    
    if CONF_LOCKED in config:
        conf = config[CONF_LOCKED]
        sens = cg.new_Pvariable(conf[CONF_ID])
        await switch.register_switch(sens, conf)
        cg.add(sens.set_parent(var))
        cg.add(var.set_locked_switch(sens))
    
    if CONF_SCREEN_COMMAND in config:
        conf = config[CONF_SCREEN_COMMAND]
        sens = cg.new_Pvariable(conf[CONF_ID])
        await button.register_button(sens, conf)
        cg.add(sens.set_parent(var))
        cg.add(sens.set_command_type(0))  # Screen command
        cg.add(var.set_screen_button(sens))
    
    if CONF_AUTO_COMMAND in config:
        conf = config[CONF_AUTO_COMMAND]
        sens = cg.new_Pvariable(conf[CONF_ID])
        await button.register_button(sens, conf)
        cg.add(sens.set_parent(var))
        cg.add(sens.set_command_type(1))  # Auto command
        cg.add(var.set_auto_button(sens))
    
    if CONF_STATUS in config:
        conf = config[CONF_STATUS]
        sens = cg.new_Pvariable(conf[CONF_ID])
        await text_sensor.register_text_sensor(sens, conf)
        cg.add(sens.set_parent(var))
        cg.add(var.set_status_sensor(sens))
    
    # Register automation triggers
    for conf in config.get(CONF_ON_CONNECTED, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)
    
    for conf in config.get(CONF_ON_DISCONNECTED, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)
    
    for conf in config.get(CONF_ON_VERIFIED, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)
    
    for conf in config.get(CONF_ON_MESSAGE, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(cg.std_string, "message")], conf)