from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from homeassistant.helpers.event import track_state_change

from homeassistant.components.climate import (
    STATE_HEAT, STATE_COOL, STATE_IDLE, ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT, STATE_ON, STATE_OFF, ATTR_TEMPERATURE)

import logging
import json
from datetime import timedelta

CONST_MODE_SMART_SCHEDULE = "SMART_SCHEDULE" # Default mytado mode
CONST_MODE_OFF = "OFF"                       # Switch off heating in a zone 

# When we change the temperature setting, we need an overlay mode
CONST_OVERLAY_TADO_MODE = "TADO_MODE" # wait until tado changes the mode automatic
CONST_OVERLAY_MANUAL    = "MANUAL"    # the user has change the temperature or mode manually
CONST_OVERLAY_TIMER     = "TIMER"     # the temperature will be reset after a timespan

CONST_DEFAULT_OPERATION_MODE = CONST_OVERLAY_TADO_MODE # will be used when changing temperature
CONST_DEFAULT_OFF_MODE       = CONST_OVERLAY_MANUAL    # will be used when switching to CONST_MODE_OFF

# DOMAIN = 'tado_v1'

_LOGGER = logging.getLogger(__name__)
SENSOR_TYPES = ['temperature', 'humidity', 'heating', 'tado mode', 'power']

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the climate platform."""

    # get the PyTado object from the hub component
    tado = hass.data['Mytado']

    try:   
        zones = tado.getZones()
    except RuntimeError as error:
        _LOGGER.error("Unable to get zone info from mytado", error)
        return False

    tadoData = TadoData(tado)
        
    climateDevices = []
    for zone in zones:
        climateDevices.append(tadoData.createClimateDevice(hass, zone['name'], zone['id']))
    
    if len(climateDevices)> 0:
        add_devices(climateDevices)
        tadoData.activateTracking(hass)        
        return True
    else:
        return False

class TadoClimate(ClimateDevice):
    """Representation of a tado climate device."""
    
    def __init__(self, tado, zoneName, zoneID, 
                 min_temp, max_temp, target_temp, ac_mode,
                 tolerance = 0.3):        
        self._tado = tado
        self.zoneName = zoneName
        self.zoneID = zoneID

        self.ac_mode = ac_mode

        self._active = False
        self._device_is_active = False
        
        self._cur_temp = None
        self._cur_humidity = None
        self._is_away = False
        self._min_temp = min_temp
        self._max_temp = max_temp
        self._target_temp = target_temp
        self._tolerance = tolerance
        self._unit = TEMP_CELSIUS
        
        self._operation_list = [CONST_OVERLAY_MANUAL, CONST_OVERLAY_TIMER, CONST_OVERLAY_TADO_MODE, CONST_MODE_SMART_SCHEDULE, CONST_MODE_OFF]
        self._current_operation = CONST_MODE_SMART_SCHEDULE
        self._overlay_mode = self._current_operation
        
    @property
    def should_poll(self):
        """No Polling needed for tado climate device (because it reuses sensors)."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.zoneName

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._cur_humidity
        
    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return self._cur_temp
        
    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self._current_operation

    @property
    def operation_list(self):
        """List of available operation modes."""
        return self._operation_list

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return self._is_away
    
    @property
    def _is_device_active(self):
        """If the toggleable device is currently active."""
        return self._device_is_active
        
    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temp

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._current_operation = CONST_DEFAULT_OPERATION_MODE
        self._overlay_mode = None
        self._target_temp = temperature
        self._control_heating()
        self.update_ha_state()

    def set_operation_mode(self, operation_mode):
        """Set new target temperature."""
        self._current_operation = operation_mode
        self._overlay_mode = None
        self._control_heating()
        self.update_ha_state()

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        # pylint: disable=no-member
        if self._min_temp:
            return self._min_temp
        else:
            # get default temp from super class
            return ClimateDevice.min_temp.fget(self)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        # pylint: disable=no-member
        if self._max_temp:
            return self._max_temp
        else:
            # Get default temp from super class
            return ClimateDevice.max_temp.fget(self)

    def sensorChanged(self, entity_id, old_state, new_state):
        """Called when a depending sensor changes."""
        if new_state is None or new_state.state is None:
            return
            
        self.updateState(entity_id, new_state, True)
        
        if entity_id.endswith("temperature"):
            self._control_heating()

    def updateState(self, type, state, updateHa):
        try:
            if type.endswith("temperature"):
                unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

                self._cur_temp = self.hass.config.units.temperature(
                    float(state.state), unit)

                self._target_temp = self.hass.config.units.temperature(
                    float(state.attributes.get("setting")), unit)

            if type.endswith("humidity"):
                self._cur_humidity = float(state.state)

            if type.endswith("heating"):
                heating_percent = float(state.state)

                self._device_is_active = heating_percent > 0

            if type.endswith("tado mode"):
                self._is_away = state.state == "AWAY"
                
            if type.endswith("power"):
                if state.state == "OFF":
                    self._current_operation = CONST_MODE_OFF
                    self._device_is_active = false

            if updateHa:
                self.schedule_update_ha_state()

        except ValueError as ex:
            _LOGGER.error('Unable to update from sensor: {}'.format(type), ex)

    def _control_heating(self):
        """Send new target temperature to mytado."""
        if not self._active and None not in (self._cur_temp,
                                             self._target_temp):
            self._active = True
            _LOGGER.info('Obtained current and target temperature. '
                         'tado thermostat active.')

        if not self._active or self._current_operation == self._overlay_mode:
            return
        
        if self._current_operation == CONST_MODE_SMART_SCHEDULE:
            _LOGGER.info('Switching mytado.com to SCHEDULE (default) for zone %s', self.zoneName)
            self._tado.setZoneOverlay(self.zoneID, self._current_operation)
            self._overlay_mode = self._current_operation
            return

        if self._current_operation == CONST_MODE_OFF:
            _LOGGER.info('Switching mytado.com to OFF for zone %s', self.zoneName)
            self._tado.setZoneOverlay(self.zoneID, CONST_DEFAULT_OFF_MODE)
            self._overlay_mode = self._current_operation
            return
        
        if self.ac_mode == False:
            is_heating = self._is_device_active
            if is_heating:
                too_hot = self._cur_temp - self._target_temp > self._tolerance
                if too_hot:
                    _LOGGER.info('Switching mytado.com to schedule mode for zone %s', self.zoneName)
                    self._tado.resetZoneOverlay(self.zoneID)
                    self._current_operation = CONST_MODE_SMART_SCHEDULE
            else:
                too_cold = self._target_temp - self._cur_temp > self._tolerance
                if too_cold:
                    _LOGGER.info('Activating mytado.com heating for zone %s', self.zoneName)
                    self._tado.setZoneOverlay(self.zoneID, self._current_operation, self._target_temp)

        self._overlay_mode = self._current_operation

class TadoData(object):
    def __init__(self, tado):
        self._tado = tado
        self._tracking_active = False
        
        self.sensors = []
    
    def createClimateDevice(self, hass, name, id):
        capabilities = self._tado.getCapabilities(id)

        min_temp = float(capabilities["temperatures"]["celsius"]["min"])
        max_temp = float(capabilities["temperatures"]["celsius"]["max"])
        target_temp = 21
        ac_mode = capabilities["type"] != "HEATING"
        
        deviceID = 'climate {} {}'.format(name, id)
        device = TadoClimate(self._tado, name, id,
                             min_temp, max_temp, target_temp, ac_mode)
        sensor = {
            "id"      : deviceID,
            "device"  : device,
            "sensors" : []
        }
        
        self.sensors.append(sensor)
        
        for sensor_type in SENSOR_TYPES:
            entity_id = 'sensor.{} {}'.format(name, sensor_type).lower().replace(" ", "_")
            sensor["sensors"].append(entity_id)

            sensor_state = hass.states.get(entity_id)
            if sensor_state:
                self.updateState(sensor_type, sensor_state, False)

        return device

    def activateTracking(self, hass):
        if self._tracking_active is False:
            for data in self.sensors:
                for entity_id in data["sensors"]:
                    track_state_change(hass, entity_id, data["device"].sensorChanged)
                    _LOGGER.info('activated state tracking for {}.'.format(entity_id))

        self._tracking_active = True

        