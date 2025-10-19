#pragma once
#include "esphome/components/text_sensor/text_sensor.h"
#include "hikeit_ble.h"

namespace esphome {
namespace hikeit_ble {

class HikeITStatusSensor : public text_sensor::TextSensor, public Component {
 public:
  void set_parent(HikeITBLEComponent *parent) { this->parent_ = parent; }
  
 protected:
  HikeITBLEComponent *parent_{nullptr};
};

}  // namespace hikeit_ble
}  // namespace esphome