import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import text_sensor
from esphome.const import CONF_ID
from .. import hikeit_ble_ns, HikeITBLEComponent, CONF_HIKEIT_BLE_ID

HikeITStatusSensor = hikeit_ble_ns.class_("HikeITStatusSensor", text_sensor.TextSensor, cg.Component)

CONFIG_SCHEMA = text_sensor.text_sensor_schema(HikeITStatusSensor).extend({
    cv.GenerateID(CONF_HIKEIT_BLE_ID): cv.use_id(HikeITBLEComponent),
})

async def to_code(config):
    var = await text_sensor.new_text_sensor(config)
    await cg.register_component(var, config)
    parent = await cg.get_variable(config[CONF_HIKEIT_BLE_ID])
    cg.add(var.set_parent(parent))