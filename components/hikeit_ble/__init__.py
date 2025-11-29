import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.components import ble_client, switch
from esphome.const import (
    CONF_ID,
    CONF_MAC_ADDRESS,
    CONF_TRIGGER_ID,
)

DEPENDENCIES = ["ble_client"]
CODEOWNERS = ["@andrewbackway"]

# Component namespace
hikeit_ble_ns = cg.esphome_ns.namespace("hikeit_ble")

# Main component class
HikeITBLEComponent = hikeit_ble_ns.class_(
    "HikeITBLEComponent", 
    cg.Component,
    ble_client.BLEClientNode
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
CONF_ON_CONNECTED = "on_connected"
CONF_ON_DISCONNECTED = "on_disconnected"
CONF_ON_VERIFIED = "on_verified"
CONF_ON_MESSAGE = "on_message"
CONF_CONNECT_SWITCH = "connect_switch"

# Speed model options (exported for platform components)
SPEED_MODELS = [
    "Off",
    "Eco 4x4",
    "Cruise",
    "Sport",
    "Hike IT",
    "Auto",
    "Launch",
    "Anti-Slip",
    "Valet"
    #"SL" Unknown does not correspond to option on device
]

# Component configuration schema
CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(HikeITBLEComponent),
            cv.Required(CONF_MAC_ADDRESS): cv.mac_address,
            cv.Optional(CONF_PIN, default="123"): cv.string,
            cv.Optional(CONF_CONNECT_SWITCH): cv.use_id(switch.Switch),
            
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
    mac_str = str(config[CONF_MAC_ADDRESS])
    mac_bytes = [int(b, 16) for b in mac_str.split(":")]
    mac_int = 0
    for b in mac_bytes:
        mac_int = (mac_int << 8) | b
    cg.add(var.set_address(mac_int))
    
    # Set PIN
    cg.add(var.set_pin(config[CONF_PIN]))
    
    if CONF_CONNECT_SWITCH in config:
        sw = await cg.get_variable(config[CONF_CONNECT_SWITCH])
        cg.add(var.set_connect_switch(sw))
    
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