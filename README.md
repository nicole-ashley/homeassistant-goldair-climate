Home Assistant Goldair WiFi Heater component
============================================

The `goldair_heater` component integrates 
[Goldair WiFi-enabled heaters](http://www.goldair.co.nz/product-catalogue/heating/wifi-heaters) into Home Assistant, 
enabling control of setting the following parameters via the UI and the following services:

**Climate**
* **power** (on/off)
* **mode** (Comfort, Eco, Anti-freeze)
* **target temperature** (`5`-`35` in Comfort mode, `5`-`21` in Eco mode, in °C)
* **power level** (via the swing mode setting because no appropriate HA option exists: `Auto`, `1`-`5`, `Stop`)

Current temperature is also displayed.

**Sensor**
* **current temperature** (in °C)

**Light**
* **LED display** (on/off)

**Lock**
* **Child lock** (on/off)

---

### Warning
Please note, this component has currently only been tested with the Goldair GPPH (inverter) range, however theoretically 
it should also work with GEPH and GPCV devices and any other Goldair heaters based on the Tuya platform.

---

To enable the component, copy the contents of this repository's `component` directory to your
`<config_dir>/custom_components` directory, then add the following lines to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry
goldair_heater:
  - name: My heater
    host: 1.2.3.4
    device_id: <your device id>
    local_key: <your local key>
```

CONFIGURATION VARIABLES
-----------------------

### name
&nbsp;&nbsp;&nbsp;&nbsp;*(string) (Required)* Any unique for the device; required because the Tuya API doesn't provide
                                              the one you set in the app.

### host
&nbsp;&nbsp;&nbsp;&nbsp;*(string) (Required)* IP or hostname of the device.

### device_id
&nbsp;&nbsp;&nbsp;&nbsp;*(string) (Required)* Device ID retrieved from the Goldair app logs (see below).

### local_key
&nbsp;&nbsp;&nbsp;&nbsp;*(string) (Required)* Local key retrieved from the Goldair app logs (see below).

### climate
&nbsp;&nbsp;&nbsp;&nbsp;*(boolean) (Optional)* Whether to surface this heater as a climate device.

&nbsp;&nbsp;&nbsp;&nbsp;*Default value: true* 

### sensor
&nbsp;&nbsp;&nbsp;&nbsp;*(boolean) (Optional)* Whether to surface this heater's thermometer as a temperature sensor.

&nbsp;&nbsp;&nbsp;&nbsp;*Default value: false* 

### display_light
&nbsp;&nbsp;&nbsp;&nbsp;*(boolean) (Optional)* Whether to surface this heater's LED display control as a light.

&nbsp;&nbsp;&nbsp;&nbsp;*Default value: false* 

### child_lock
&nbsp;&nbsp;&nbsp;&nbsp;*(boolean) (Optional)* Whether to surface this heater's child lock as a lock device.

&nbsp;&nbsp;&nbsp;&nbsp;*Default value: false* 

GOTCHAS
-------
These heaters have individual target temperatures for their Comfort and Eco modes, whereas Home Assistant only supports
a single target temperature. Therefore, when you're in Comfort mode you will set the Comfort temperature (`5`-`35`), and
when you're in Eco mode you will set the Eco temperature (`5`-`21`), just like you were using the heater's own control 
panel. Bear this in mind when writing automations that change the operation mode and set a temperature at the same time: 
you must change the operation mode *before* setting the new target temperature, otherwise you will set the current 
thermostat rather than the new one. 

When switching to Anti-freeze mode, the heater will set the current power level to `1` as if you had manually chosen it.
When you switch back to other modes, you will no longer be in `Auto` and will have to set it again if this is what you
wanted. This could be worked around in code however it would require storing state that may be cleared if HA is
restarted and due to this unreliability it's probably best that you just factor it into your automations.

When child lock is enabled, the heater's display will flash with the child lock symbol (`[]`) whenever you change
something in HA. This can be confusing because it's the same behaviour as when you try to change something via the
heater's own control panel and the change is rejected due to being locked, however rest assured that the changes *are* 
taking effect.

FINDING YOUR DEVICE ID AND LOCAL KEY
------------------------------------

You can use an Android phone and two apps (the Goldair app and a Package Capture app) to identify your Goldair Tuya based heater(s) uuid and local key. The steps are:   

1. Download the [Goldair app from the Play Store](https://play.google.com/store/apps/details?id=com.goldair.smart).
2. Follow the instructions in the app to set up the heater. Don't agonise over the name because you'll be giving it a 
   new one in HA.
3. Once this is done and you've verified that you can control the heater from your phone, close the Goldair app.
4. Return to the Play Store on your phone, and download the "Package Capture" app (https://play.google.com/store/apps/details?id=app.greyshirts.sslcapture) and then install it. 
5. When you first open the app it will ask you to install a certificate, this is needed for it to work, so agree to install it.
6. In the top bar of the app there are two "Play" symbols. The one with a 1 allows you to capture packets from certain apps.
7. Click on the '1' play symbol, scroll down the list of apps and select "Goldair" app from the list.
8. A popup message will appear about setting up a vpn, so agree to this, and the app will then start capturing packets.
9. Leaving the Package Capture app running on your phone, next open the Goldair app. On the openeing screen showing "All Devices" pull down the screen to cause a refresh. You can do this once or twice if you wish, but once should be enough. 
10. Go back to the Packet Capture app and hit the Stop button at the top.
11. You should now have an entry below listing an x number of captures.Tap that entry to open it. 
12. Next look at the list of packets and open one of the packets in the list that is marked as "SSL". If you refreshed the screen once or twice you should have only a couple of SSL related packets in the list. 
13. In the opened packet, scroll down through the first few blocks and you should see a large JSON block. This contains a lot of code. Scroll through it looking for an `uuid` entry. There should be one for each heater that you have (if you have more than one). Copy the unique 'uuid' code for each device. If you have more than one heater, remember to write down which heater the uuid code is for. 
14. Continue to scroll throught the large JSON block and look for a few lines like the ones below:

"devAttribute": 0
"name": Smart Socket 4"
"timezoneId": "Europe/London"
"localKey": "XXXXXXXXXXXXXXX"

There should be one for each heater that you have (if you have more than one). Copy the unique 'uuid' code for each device. If you have more than one heater, remember to write down which device the localkey code is for. 

15. Copy the value of `uuid` (eg: 1234567890abcdef1234) to `device_id`, and the value of `localKey` 
   (eg: 1234567890abcdef) to `local_key` in your `configuration.yaml` file. If you have more than one heater, you will need more than one entry for the Goldair_heater component. 

Repeat steps 13 and 14 looking for the 'uuid' and "localkey" in the JSON block for as many heaters as you have to set up.

An alternate method is at
[codetheweb/tuyapi](https://github.com/codetheweb/tuyapi/blob/master/docs/SETUP.md) (you're looking for the `uuid` and
`localKey` values).

NEXT STEPS
----------
This component needs specs! Once they're written I'm considering submitting it to the HA team for inclusion in standard 
installations. Please report any issues and feel free to raise pull requests.

This was my first Python project, so feel free to correct any conventions or idioms I got wrong.

ACKNOWLEDGEMENTS
----------------
All I did was write some code. None of this would have been possible without:

* [TarxBoy](https://github.com/TarxBoy)'s [investigation using codetheweb/tuyapi](https://github.com/codetheweb/tuyapi/issues/31) to figure out the correlation of the cryptic DPS states 
* [sean6541](https://github.com/sean6541)'s [tuya-homeassistant](https://github.com/sean6541/tuya-homeassistant) library giving an example of integrating Tuya devices with Home Assistant
* [clach04](https://github.com/clach04)'s [python-tuya](https://github.com/clach04/python-tuya) library
