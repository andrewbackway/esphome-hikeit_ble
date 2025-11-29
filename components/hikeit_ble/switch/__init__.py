import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import switch
from esphome.const import CONF_ID, CONF_ICON, DEVICE_CLASS_EMPTY
from .. import hikeit_ble_ns, HikeITBLEComponent, CONF_HIKEIT_BLE_ID

DEPENDENCIES = ["hikeit_ble"]

ICON_LOCK = "mdi:lock"

HikeITLockedSwitch = hikeit_ble_ns.class_("HikeITLockedSwitch", switch.Switch, cg.Component)

CONFIG_SCHEMA = (
    switch.switch_schema(HikeITLockedSwitch, icon=ICON_LOCK, device_class=DEVICE_CLASS_EMPTY)
    .extend({
        cv.GenerateID(CONF_HIKEIT_BLE_ID): cv.use_id(HikeITBLEComponent),
    })
    .extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    var = await switch.new_switch(config)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_HIKEIT_BLE_ID])
    cg.add(var.set_parent(parent))
    cg.add(parent.set_locked_switch(var))