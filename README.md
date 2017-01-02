# A custom tado component for home-assistant
Custom home-assistant component for tado (using my fork of PyTado for a py3 compatible module)

It is highly inspired by https://community.home-assistant.io/t/tado-api-json/272/5 and the comments by diplix (https://community.home-assistant.io/users/diplix)

It is called `tado_v1` because it is build upon the unofficial API used by the myTado.com-Webapp.


# Howto use
I created a new custom_component which adds multiple sensors for every zone in myTado.com (not for every device)

## Copy files to local config directory
you have to copy all files included in `custom_components` to your home-assistant config directory.

For hass manual installation it is:

  `/home/homeassistant/.homeassistant/`
  
## Edit configuration.yaml
```
tado_v1:
    mytado_username: <.. your username ..>
    mytado_password: <.. your password ..>
```

## Use the new sensors in home-assistant
For every zone in your tado setup we will create a sensor with a specific unit
```
sensor.<name of tado zone>_temperature         (°C)
sensor.<name of tado zone>_temperature_setting (°C)
sensor.<name of tado zone>_temperature_time    (string)
sensor.<name of tado zone>_humidity            (%)
sensor.<name of tado zone>_humidity_time       (string)
sensor.<name of tado zone>_heating             (%)
sensor.<name of tado zone>_heating_time        (string)
sensor.<name of tado zone>_heating_mode        (string)
sensor.<name of tado zone>_power               (string)
sensor.<name of tado zone>_link                (string)
sensor.<name of tado zone>_tado_mode           (string)
```
and one sensor for the bridge
```
sensor.<name of tado home>_tado_bridge_status  (boolean)
```

# Links
* Home-Assistant (http://home-assistant.io)
* PyTado (https://github.com/chrism0dwk/PyTado) -> (https://github.com/wmalgadey/tado_component)
