from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

import logging
import json
from datetime import timedelta

# DOMAIN = 'tado_v1'

_LOGGER = logging.getLogger(__name__)
SENSOR_TYPES = ['temperature', 'humidity', 'power',
   'link', 'heating', 'tado mode']


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""

    # get the PyTado object from the hub component
    tado = hass.data['Mytado']

    try:   
        zones = tado.getZones()
    except RuntimeError as error:
        _LOGGER.error("Unable to get zone info from mytado", error)
        return False

    tadoData = TadoData(tado, timedelta(seconds=15))
        
    sensorItems = []
    for zone in zones:
        if zone['type'] == 'HEATING':
            for variable in SENSOR_TYPES:
                sensorItems.append(tadoData.createZoneSensor(zone, zone['name'], zone['id'], variable))

    meData = tado.getMe()
    sensorItems.append(tadoData.createDeviceSensor(meData, meData['homes'][0]['name'], meData['homes'][0]['id'], "tado bridge status"))

    tadoData.update()
    
    if len(sensorItems)> 0:
        add_devices(sensorItems)
        return True
    else:
        return False

class TadoSensor(Entity):
    """Representation of a tado Sensor."""
    
    def __init__(self, tadoData, zoneName, zoneId, zoneVariable, dataID):
        self._tadoData = tadoData
        self.zoneName = zoneName
        self.zoneID = zoneId
        self.zoneVariable = zoneVariable
        self.uniqueID = '{} {}'.format(zoneVariable, zoneId)
        self._dataID = dataID

        self._state = None
        self._stateAttributes = None

    @property
    def should_poll(self):
        """Polling needed for tado sensors."""
        return True

    @property
    def unique_id(self):
        """Return the unique id"""
        return self.uniqueID

    @property
    def name(self):
        """Return the name of the sensor."""
        return '{} {}'.format(self.zoneName, self.zoneVariable)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def state_attributes(self):
        """Return the state attributes.
        Implemented by component base class.
        """
        return self._stateAttributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if self.zoneVariable == "temperature":
            return TEMP_CELSIUS
        elif self.zoneVariable == "humidity":
            return '%'
        elif self.zoneVariable == "heating":
            return '%'
            
    @property
    def icon(self):
        if self.zoneVariable == "temperature":
            return 'mdi:thermometer'
        elif self.zoneVariable == "humidity":
            return 'mdi:water-percent'

    def update(self):
        self._tadoData.update()

        self.pushUpdate(self._tadoData.getData(self._dataID), True)

    def pushUpdate(self, data, updateHa):
        if self.zoneVariable == 'temperature':
            if 'sensorDataPoints' in data:
                self._state = float(data['sensorDataPoints']['insideTemperature']['celsius'])
                self._stateAttributes = {
                    "time": data['sensorDataPoints']['insideTemperature']['timestamp'],
                    "setting": float(data['setting']['temperature']['celsius'])
                }
        elif self.zoneVariable == 'humidity':
            if 'sensorDataPoints' in data:
                self._state = float(data['sensorDataPoints']['humidity']['percentage'])
                self._stateAttributes = {
                    "time": data['sensorDataPoints']['humidity']['timestamp'],
                }
        elif self.zoneVariable == 'power':
            if 'setting' in data:
                self._state = data['setting']['power']
        elif self.zoneVariable == 'link': 
            if 'link' in data:
                self._state = data['link']['state']
        elif self.zoneVariable == 'heating': 
            if 'activityDataPoints' in data:
                self._state = float(data['activityDataPoints']['heatingPower']['percentage'])
                self._stateAttributes = {
                    "time": data['activityDataPoints']['heatingPower']['timestamp'],
                }
        elif self.zoneVariable == 'tado bridge status':
            if 'connectionState' in data:
                self._state = data['connectionState']['value']
        elif self.zoneVariable == 'tado mode':
            if 'tadoMode' in data:
                self._state = data['tadoMode']

        if updateHa:
            super().update_ha_state()

class TadoData(object):
    def __init__(self, tado, interval):
        self._tado = tado
        self._interval = interval
        
        self.sensors = {}
        self.data = {}
        
        # Apply throttling to methods using configured interval
        self.update = Throttle(interval)(self._update)
    
    def createZoneSensor(self, zone, name, id, variable):
        dataID = 'zone {} {}'.format(name, id)
        
        self.sensors[dataID] = { 
            "zone"   : zone,
            "name"   : name,
            "id"     : id,
            "dataID" : dataID
        }
        self.data[dataID] = None
            
        return TadoSensor(self, name, id, variable, dataID)
        
    def createDeviceSensor(self, device, name, id, variable):
        dataID = 'device {} {}'.format(name, id)
        
        self.sensors[dataID] = { 
            "device" : device,
            "name"   : name,
            "id"     : id,
            "dataID" : dataID
        }
        self.data[dataID] = None
            
        return TadoSensor(self, name, id, variable, dataID)
    
    def getData(self, dataID):
        data = { "error" : "no data" }

        if dataID in self.data:
            data = self.data[dataID]

        return data        
    
    def _update(self):
        _LOGGER.info("querying myTado.com")
    
        for dataID, sensor in self.sensors.items():
            data = None

            try:
                if "zone" in sensor:
                    data = self._tado.getState(sensor["id"])
                if "device" in sensor:
                    data = self._tado.getDevices()[0]

            except (RuntimeError) as error:
                _LOGGER.error("Unable to connect to myTado. %s", error)
        
            self.data[dataID] = data
            
            #_LOGGER.info(json.dumps(data))
