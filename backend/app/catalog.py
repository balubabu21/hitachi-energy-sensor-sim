"""Catalogue of Hitachi Energy product families and the sensors they could carry.

Product names, groupings and short descriptions are paraphrased from the
public Hitachi Energy "Products and solutions" pages
(https://www.hitachienergy.com/products-and-solutions). Sensors, fields and
ranges are *engineering assumptions* for simulation purposes only — they are
not Hitachi Energy specifications.

Software-only offerings (Asset & Work Management, Energy Portfolio
Management, Network Control, Cybersecurity, Digitalization) are excluded
because they consume sensor data rather than produce it.
"""
from __future__ import annotations

from .models import Product, SensorSpec, counter, enum, flag, integer, num, phases

BASE = "https://www.hitachienergy.com/products-and-solutions"
QUALITY = {"GOOD": 0.96, "UNCERTAIN": 0.03, "BAD": 0.01}

PRODUCTS: list[Product] = [
    # ------------------------------------------------------------------ Transformers
    Product(
        id="power-transformer",
        name="Power Transformers",
        group="Transformers",
        description=(
            "Full range of power transformers that are key components of power networks, "
            "including generator step-up, HVDC converter, shell and intertie transformers. "
            "TXpert™ Enabled digital units give early warning to help prevent failures."
        ),
        url=f"{BASE}/transformers/power-transformers",
        examples=["TXpert™ Enabled digital transformer", "Generator step-up (GSU)", "HVDC converter transformer",
                  "CompactStar™", "TXpand™ rupture-resistant"],
        sensors=[
            SensorSpec(
                id="dga-monitor", name="Dissolved Gas Analysis (DGA) monitor",
                description="Online multi-gas analyser that extracts gases from the insulating oil to detect arcing, overheating and partial discharge.",
                principle="Photo-acoustic / IR spectroscopy on head-space gas", protocol="IEC 61850 / DNP3", sample_interval_s=3600,
                fields=[
                    num("hydrogen_h2", "ppm", 0, 2000, 40, "Hydrogen – indicator of partial discharge", 1),
                    num("methane_ch4", "ppm", 0, 1000, 25, "Methane – low-temperature overheating", 1),
                    num("ethane_c2h6", "ppm", 0, 1000, 20, "Ethane – thermal fault", 1),
                    num("ethylene_c2h4", "ppm", 0, 1000, 15, "Ethylene – high-temperature thermal fault", 1),
                    num("acetylene_c2h2", "ppm", 0, 500, 0.5, "Acetylene – arcing", 2),
                    num("carbon_monoxide_co", "ppm", 0, 5000, 300, "CO – cellulose (paper) degradation", 1),
                    num("carbon_dioxide_co2", "ppm", 0, 20000, 2500, "CO2 – cellulose ageing", 0),
                    num("oxygen_o2", "ppm", 0, 30000, 8000, "Dissolved oxygen", 0),
                    num("tdcg", "ppm", 0, 10000, 420, "Total dissolved combustible gas", 0),
                    enum("duval_zone", {"PD": 0.02, "T1": 0.05, "T2": 0.02, "T3": 0.01, "D1": 0.01, "D2": 0.005, "DT": 0.005, "NORMAL": 0.88},
                         "Duval triangle fault classification"),
                ],
            ),
            SensorSpec(
                id="moisture-in-oil", name="Moisture-in-oil sensor",
                description="Capacitive thin-film probe immersed in oil measuring water activity, used to assess insulation ageing.",
                principle="Capacitive polymer thin-film", protocol="Modbus RTU / 4-20 mA", sample_interval_s=600,
                fields=[
                    num("water_content", "ppm", 0, 80, 12, "Water dissolved in oil", 1),
                    num("relative_saturation", "%", 0, 100, 8, "Relative saturation of water in oil", 1),
                    num("oil_temperature", "°C", -40, 120, 55, "Oil temperature at probe", 1),
                ],
            ),
            SensorSpec(
                id="thermal-monitor", name="Thermal / fibre-optic hot-spot monitor",
                description="Fibre-optic probes in windings plus PT100 RTDs for top/bottom oil and ambient temperature.",
                principle="Fluorescent fibre-optic + PT100 RTD", protocol="IEC 61850", sample_interval_s=60,
                fields=[
                    num("top_oil_temp", "°C", -40, 130, 62, "Top-oil temperature", 1),
                    num("bottom_oil_temp", "°C", -40, 110, 45, "Bottom-oil temperature", 1),
                    phases("winding_hotspot_temp", "°C", -40, 160, 78, "Winding hot-spot temperature per phase", 1),
                    num("ambient_temp", "°C", -50, 55, 18, "Ambient air temperature", 1),
                    num("ageing_rate", "p.u.", 0, 20, 0.8, "Relative insulation ageing rate (IEC 60076-7)", 3),
                ],
            ),
            SensorSpec(
                id="bushing-monitor", name="Bushing monitor",
                description="Measures leakage current through the bushing test tap to track capacitance and dielectric dissipation factor.",
                principle="Test-tap leakage current sensing", protocol="IEC 61850", sample_interval_s=300,
                fields=[
                    phases("capacitance_c1", "pF", 200, 800, 450, "Main insulation capacitance C1", 1),
                    phases("tan_delta", "%", 0.1, 2.0, 0.35, "Dissipation factor (tan δ)", 3),
                    phases("leakage_current", "mA", 0, 200, 60, "Leakage current via test tap", 2),
                ],
            ),
            SensorSpec(
                id="oltc-monitor", name="On-load tap-changer (OLTC) monitor",
                description="Tracks tap position, drive motor signature and contact wear of the tap-changer.",
                principle="Motor current + position encoder", protocol="IEC 61850", sample_interval_s=60,
                fields=[
                    integer("tap_position", None, 1, 33, 17, "Current tap position"),
                    counter("operation_count", "ops", 120000, 999999, 1, "Cumulative tap operations"),
                    num("motor_current", "A", 0, 10, 2.1, "Drive motor current during last operation", 2),
                    num("operation_time", "s", 3, 8, 5.2, "Duration of last tap change", 2),
                    num("contact_wear", "%", 0, 100, 22, "Estimated diverter contact wear", 1),
                    num("diverter_oil_temp", "°C", -40, 110, 50, "Diverter compartment oil temperature", 1),
                ],
            ),
            SensorSpec(
                id="partial-discharge", name="UHF / acoustic partial-discharge sensor",
                description="UHF drain-valve probes and acoustic emission sensors locating internal partial discharge.",
                principle="UHF antenna (300 MHz–3 GHz) + piezo acoustic", protocol="IEC 61850", sample_interval_s=60,
                fields=[
                    num("apparent_charge", "pC", 0, 5000, 50, "Apparent charge magnitude", 0),
                    integer("pulse_rate", "pulses/s", 0, 10000, 20, "PD pulse repetition rate"),
                    num("uhf_peak_level", "dBm", -90, 0, -70, "UHF peak signal level", 1),
                    enum("pd_pattern", {"NONE": 0.9, "CORONA": 0.04, "SURFACE": 0.03, "INTERNAL_VOID": 0.02, "FLOATING": 0.01}, "PRPD pattern classification"),
                ],
            ),
            SensorSpec(
                id="cooling-control", name="Cooling system sensor set",
                description="Status and performance of fans, oil pumps and radiators (ONAN/ONAF/OFAF).",
                principle="Current transducers, flow meters, contacts", protocol="Modbus TCP", sample_interval_s=60,
                fields=[
                    enum("cooling_stage", {"ONAN": 0.6, "ONAF1": 0.25, "ONAF2": 0.12, "OFAF": 0.03}, "Active cooling stage"),
                    integer("fans_running", None, 0, 12, 4, "Number of fans running"),
                    num("oil_pump_flow", "l/min", 0, 3000, 900, "Forced-oil pump flow", 0),
                    num("radiator_delta_t", "K", 0, 40, 12, "Temperature drop across radiators", 1),
                    flag("fan_failure_alarm", "Fan motor failure detected", 0.01),
                ],
            ),
            SensorSpec(
                id="protection-devices", name="Mechanical protection devices",
                description="Buchholz relay, pressure relief device, oil level gauge and rapid pressure rise relay.",
                principle="Float switches, pressure transducers", protocol="Hard-wired contacts / IEC 61850", sample_interval_s=10,
                fields=[
                    num("buchholz_gas_volume", "ml", 0, 300, 0, "Gas accumulated in Buchholz relay", 1),
                    flag("buchholz_alarm", "Buchholz alarm stage", 0.002),
                    flag("buchholz_trip", "Buchholz trip stage", 0.0005),
                    num("tank_pressure", "kPa", -20, 70, 8, "Tank internal pressure (gauge)", 2),
                    flag("prd_operated", "Pressure relief device operated", 0.0005),
                    num("oil_level", "%", 0, 100, 72, "Conservator oil level", 1),
                ],
            ),
            SensorSpec(
                id="electrical-measurement", name="Load measurement (CT/VT)",
                description="Bushing CTs and VTs measuring load, voltage and power flow through the transformer.",
                principle="Current & voltage transformers via IED", protocol="IEC 61850-9-2", sample_interval_s=1,
                fields=[
                    phases("hv_voltage", "kV", 0, 450, 400, "HV side phase-to-phase voltage", 2),
                    phases("hv_current", "A", 0, 2000, 650, "HV side line current", 1),
                    num("active_power", "MW", -800, 800, 420, "Active power flow", 2),
                    num("reactive_power", "Mvar", -300, 300, 60, "Reactive power flow", 2),
                    num("load_factor", "%", 0, 150, 68, "Loading relative to rating", 1),
                    num("frequency", "Hz", 49.5, 50.5, 50.0, "System frequency", 3),
                    num("dc_bias_current", "A", 0, 50, 0.5, "Neutral DC / GIC current (DC Mitigator)", 2),
                ],
            ),
            SensorSpec(
                id="tank-vibration", name="Tank vibration sensor",
                description="Accelerometers on the tank wall to detect core/winding looseness.",
                principle="MEMS / piezo accelerometer", protocol="Modbus TCP", sample_interval_s=60,
                fields=[
                    num("vibration_rms", "mm/s", 0, 20, 1.8, "Overall vibration velocity RMS", 2),
                    num("amplitude_100hz", "µm", 0, 50, 4, "Amplitude at 2× line frequency", 2),
                    num("noise_level", "dB(A)", 40, 110, 72, "Sound pressure level", 1),
                ],
            ),
        ],
    ),
    Product(
        id="distribution-transformer",
        name="Distribution Transformers",
        group="Transformers",
        description=(
            "Liquid-filled distribution transformers that step medium voltage down for end users, "
            "including pole-mounted, pad-mounted and EconiQ™ eco-efficient designs."
        ),
        url=f"{BASE}/transformers",
        examples=["Pole-mounted", "Pad-mounted", "EconiQ™ transformers", "Smart distribution transformer"],
        sensors=[
            SensorSpec(
                id="dt-smart-monitor", name="Smart transformer monitor",
                description="Compact IoT unit measuring LV load, voltage quality and oil temperature.",
                principle="Split-core CTs, voltage taps, PT100", protocol="MQTT / LTE-M", sample_interval_s=300,
                fields=[
                    phases("lv_voltage", "V", 180, 260, 230, "LV phase-to-neutral voltage", 1),
                    phases("lv_current", "A", 0, 1500, 420, "LV phase current", 1),
                    num("apparent_power", "kVA", 0, 1250, 380, "Apparent power", 1),
                    num("power_factor", None, 0.5, 1.0, 0.95, "Power factor", 3),
                    num("thd_voltage", "%", 0, 15, 2.5, "Voltage total harmonic distortion", 2),
                    num("top_oil_temp", "°C", -40, 110, 48, "Top-oil temperature", 1),
                    num("tank_pressure", "kPa", -20, 50, 3, "Tank pressure", 2),
                    num("oil_level", "%", 0, 100, 90, "Oil level", 1),
                    flag("door_open", "Enclosure/kiosk door open", 0.005),
                ],
            ),
        ],
    ),
    Product(
        id="dry-type-transformer",
        name="Dry-type Transformers",
        group="Transformers",
        description=(
            "Dry-type and cast-resin transformers for indoor, urban, data-centre and renewable "
            "applications where fire safety and low maintenance matter."
        ),
        url=f"{BASE}/transformers",
        examples=["Cast-resin", "Vacuum pressure impregnated (VPI)", "RESIBLOC®"],
        sensors=[
            SensorSpec(
                id="dry-winding-temp", name="Winding temperature controller",
                description="PT100 sensors embedded in each LV winding driving fans and alarms.",
                principle="PT100 RTD", protocol="Modbus RTU", sample_interval_s=30,
                fields=[
                    phases("winding_temp", "°C", -25, 180, 95, "Winding temperature per phase", 1),
                    num("core_temp", "°C", -25, 150, 80, "Core temperature", 1),
                    num("enclosure_ambient", "°C", -25, 50, 28, "Enclosure ambient", 1),
                    num("relative_humidity", "%RH", 0, 100, 45, "Enclosure humidity", 1),
                    flag("fans_on", "Forced-air fans running", 0.2),
                    enum("alarm_state", {"NORMAL": 0.97, "ALARM": 0.025, "TRIP": 0.005}, "Thermal protection state"),
                ],
            ),
            SensorSpec(
                id="dry-pd", name="Partial-discharge sensor",
                description="HFCT/capacitive coupler detecting discharge in resin insulation.",
                principle="High-frequency CT", protocol="Modbus TCP", sample_interval_s=300,
                fields=[
                    num("apparent_charge", "pC", 0, 500, 5, "Apparent charge", 1),
                    integer("pulse_count", "pulses/min", 0, 5000, 3, "Pulse count"),
                ],
            ),
        ],
    ),
    # ------------------------------------------------------------------ Components
    Product(
        id="transformer-bushings",
        name="Insulation & Components (Bushings, Tap-changers)",
        group="Insulation and Components",
        description="Broad, reliable portfolio of transformer components and insulation — bushings, tap-changers and insulation materials.",
        url=f"{BASE}/insulation-and-components",
        examples=["RIP/RIS condenser bushings", "DC bushings type GSD", "VUCG / UZ tap-changers"],
        sensors=[
            SensorSpec(
                id="bushing-sensor", name="Bushing test-tap sensor",
                description="Bushing adapter measuring leakage current and phase angle for online tan δ / capacitance.",
                principle="Test-tap adapter + IED", protocol="IEC 61850", sample_interval_s=300,
                fields=[
                    num("capacitance", "pF", 200, 1000, 520, "Measured capacitance", 1),
                    num("capacitance_change", "%", -10, 10, 0.2, "Change from commissioning value", 2),
                    num("tan_delta", "%", 0.1, 2.0, 0.4, "Dissipation factor", 3),
                    num("leakage_current", "mA", 0, 200, 70, "Leakage current", 2),
                    num("flange_temp", "°C", -40, 110, 40, "Flange/head temperature", 1),
                ],
            ),
        ],
    ),
    Product(
        id="instrument-transformers",
        name="Instrument Transformers",
        group="Instrument Transformers",
        description="Current and voltage transformers from 25 kV to 800 kV for measurement, protection and control under varied atmospheric conditions.",
        url=f"{BASE}/instrument-transformers",
        examples=["Oil-insulated CT/VT", "SF6 gas-insulated CT", "Capacitor voltage transformer (CVT)", "Optical CT (FOCS)"],
        sensors=[
            SensorSpec(
                id="it-health", name="Instrument transformer health monitor",
                description="Monitors insulation medium (oil or gas), secondary output and partial discharge.",
                principle="Pressure/density switch, metal bellows level, secondary IED", protocol="IEC 61850", sample_interval_s=300,
                fields=[
                    num("secondary_current", "A", 0, 5, 1.2, "CT secondary current (1 A / 5 A class)", 3),
                    num("secondary_voltage", "V", 0, 120, 63.5, "VT secondary voltage", 2),
                    num("ratio_error", "%", -1, 1, 0.05, "Ratio error vs reference", 3),
                    num("gas_density", "kg/m³", 20, 45, 36, "SF6 / eco-gas density (gas-insulated types)", 2),
                    num("bellows_level", "%", 0, 100, 55, "Metal bellows oil expansion level", 1),
                    num("pd_level", "pC", 0, 200, 2, "Partial discharge level", 1),
                    flag("low_density_alarm", "Gas density below alarm threshold", 0.002),
                ],
            ),
        ],
    ),
    # ------------------------------------------------------------------ Switching
    Product(
        id="hv-switchgear",
        name="High-Voltage Switchgear & Breakers",
        group="High-Voltage Switchgear & Breakers",
        description="Gas-insulated (GIS), air-insulated (AIS) and hybrid switchgear and circuit breakers up to 1200 kV AC and 1100 kV DC, including EconiQ™ SF6-free options.",
        url=f"{BASE}/high-voltage-switchgear-and-breakers",
        examples=["Gas-insulated switchgear (GIS)", "Live/dead-tank circuit breakers", "PASS hybrid modules", "EconiQ™ SF6-free"],
        sensors=[
            SensorSpec(
                id="gas-density", name="Gas density monitor",
                description="Temperature-compensated density sensor per gas compartment detecting leaks of SF6 or eco-efficient gas.",
                principle="Quartz oscillator / piezo-resistive pressure + temperature", protocol="IEC 61850", sample_interval_s=60,
                fields=[
                    num("pressure_abs", "bar", 4, 9, 7.0, "Absolute gas pressure", 3),
                    num("density", "kg/m³", 25, 50, 42, "Gas density (temperature compensated)", 2),
                    num("gas_temperature", "°C", -40, 80, 25, "Gas temperature", 1),
                    num("moisture", "ppmv", 0, 500, 60, "Moisture content (dew point equivalent)", 1),
                    num("leak_rate", "%/year", 0, 2, 0.1, "Estimated annual leak rate", 3),
                    enum("density_state", {"NORMAL": 0.98, "ALARM": 0.015, "LOCKOUT": 0.005}, "Density supervision state"),
                ],
            ),
            SensorSpec(
                id="breaker-mechanism", name="Circuit-breaker operating mechanism monitor",
                description="Captures coil currents, contact travel and timing every time the breaker operates.",
                principle="Hall-effect coil CTs + rotary travel transducer", protocol="IEC 61850", sample_interval_s=60,
                fields=[
                    enum("breaker_position", {"CLOSED": 0.9, "OPEN": 0.1}, "Breaker position"),
                    counter("operation_count", "ops", 2500, 20000, 1, "Cumulative CO operations"),
                    num("opening_time", "ms", 15, 40, 24, "Last opening time", 2),
                    num("closing_time", "ms", 40, 90, 58, "Last closing time", 2),
                    num("trip_coil_current", "A", 0, 10, 3.2, "Peak trip coil current", 2),
                    num("close_coil_current", "A", 0, 10, 2.8, "Peak close coil current", 2),
                    num("contact_travel", "mm", 100, 250, 180, "Contact stroke", 1),
                    num("spring_charge_time", "s", 0, 30, 12, "Spring charging motor run time", 2),
                    num("cumulative_i2t", "kA²s", 0, 50000, 4200, "Accumulated interrupted I²t (contact erosion)", 0),
                ],
            ),
            SensorSpec(
                id="gis-pd", name="GIS UHF partial-discharge sensor",
                description="Internal UHF couplers detecting particles, floating parts and voids in GIS compartments.",
                principle="UHF disc coupler", protocol="IEC 61850", sample_interval_s=60,
                fields=[
                    num("uhf_amplitude", "dBm", -90, 0, -75, "UHF peak amplitude", 1),
                    integer("pulse_count", "pulses/s", 0, 5000, 2, "Pulse count"),
                    enum("defect_type", {"NONE": 0.92, "FREE_PARTICLE": 0.03, "FLOATING_ELECTRODE": 0.02, "PROTRUSION": 0.02, "VOID": 0.01}, "Classified defect"),
                ],
            ),
            SensorSpec(
                id="contact-temp", name="Busbar / contact temperature sensor",
                description="Wireless SAW or IR sensors measuring hot-spots at busbar joints and contacts.",
                principle="Surface acoustic wave (SAW) wireless", protocol="Modbus TCP", sample_interval_s=60,
                fields=[
                    phases("contact_temp", "°C", -40, 140, 45, "Contact temperature per phase", 1),
                    num("enclosure_temp", "°C", -40, 70, 22, "Enclosure temperature", 1),
                    num("load_current", "A", 0, 4000, 1100, "Load current", 1),
                ],
            ),
        ],
    ),
    Product(
        id="generator-circuit-breaker",
        name="Generator Circuit-Breakers (GCB)",
        group="Generator Circuit-breakers",
        description="Generator circuit-breakers that protect power-plant assets by clearing short-circuit faults between the generator and step-up transformer.",
        url=f"{BASE}/generator-circuit-breakers",
        examples=["HEC family", "HECPS", "VD4G vacuum GCB"],
        sensors=[
            SensorSpec(
                id="gcb-monitor", name="GCB condition monitor",
                description="Integrated monitoring of SF6 density, mechanism, contact wear and conductor temperatures.",
                principle="Density transducer, coil CTs, PT100", protocol="IEC 61850 / Modbus", sample_interval_s=60,
                fields=[
                    num("sf6_density", "kg/m³", 30, 50, 44, "SF6 density", 2),
                    num("hydraulic_pressure", "bar", 250, 400, 330, "Hydraulic spring mechanism pressure", 1),
                    num("opening_time", "ms", 20, 50, 33, "Last opening time", 2),
                    phases("conductor_temp", "°C", 0, 120, 72, "Main conductor temperature", 1),
                    num("contact_erosion", "%", 0, 100, 18, "Arcing contact erosion", 1),
                    num("cooling_air_temp", "°C", 0, 60, 30, "Forced cooling air temperature", 1),
                    num("generator_current", "kA", 0, 50, 18, "Generator current", 2),
                    counter("mechanical_ops", "ops", 800, 20000, 1, "Mechanical operations"),
                ],
            ),
        ],
    ),
    Product(
        id="disconnectors",
        name="Disconnectors",
        group="Disconnectors",
        description="Reliable, energy-efficient disconnectors and earthing switches that de-energize and isolate equipment for safe service and maintenance.",
        url=f"{BASE}/disconnectors",
        examples=["Centre-break", "Double-side break", "Pantograph", "Vertical-break"],
        sensors=[
            SensorSpec(
                id="disconnector-monitor", name="Disconnector drive & contact monitor",
                description="Monitors motor drive signature, position and contact temperature.",
                principle="Motor current shunt, auxiliary contacts, IR thermometer", protocol="IEC 61850", sample_interval_s=60,
                fields=[
                    enum("position", {"CLOSED": 0.88, "OPEN": 0.11, "INTERMEDIATE": 0.01}, "Switch position"),
                    num("motor_peak_current", "A", 0, 15, 4.5, "Drive motor peak current", 2),
                    num("operating_time", "s", 2, 15, 6.5, "Last operating time", 2),
                    phases("contact_temp", "°C", -40, 130, 40, "Main contact temperature (IR)", 1),
                    num("ice_thickness", "mm", 0, 20, 0, "Estimated ice coating", 1),
                    counter("operation_count", "ops", 300, 10000, 1, "Operations counter"),
                ],
            ),
        ],
    ),
    Product(
        id="surge-arresters",
        name="Surge Arresters",
        group="Surge Arresters",
        description="AC and DC surge arresters for low, medium and high voltage up to 1,100 kV that protect equipment against lightning and switching overvoltages.",
        url=f"{BASE}/surge-arresters",
        examples=["PEXLIM", "POLIM", "EXLIM", "HVDC arresters"],
        sensors=[
            SensorSpec(
                id="arrester-monitor", name="Surge arrester monitor (EXCOUNT type)",
                description="Measures total and resistive leakage current and counts surges with amplitude.",
                principle="Leakage current sensor + 3rd harmonic analysis", protocol="Wireless / IEC 61850", sample_interval_s=900,
                fields=[
                    num("total_leakage_current", "mA", 0, 5, 0.8, "Total leakage current", 3),
                    num("resistive_current_3rd_harmonic", "µA", 0, 500, 40, "Third-harmonic resistive leakage current", 1),
                    counter("surge_count", None, 12, 9999, 1, "Number of surges registered"),
                    num("last_surge_amplitude", "kA", 0, 100, 2.5, "Peak current of last surge", 2),
                    num("housing_temp", "°C", -50, 90, 25, "Housing temperature", 1),
                ],
            ),
        ],
    ),
    # ------------------------------------------------------------------ Grid systems
    Product(
        id="capacitors-filters",
        name="Capacitors and Filters",
        group="Capacitors and Filters",
        description="Capacitor banks and harmonic filters that improve power quality by compensating reactive power and absorbing harmonics.",
        url=f"{BASE}/capacitors-and-filters",
        examples=["Shunt capacitor banks", "Harmonic filters", "Capacitor units (internal fuse)"],
        sensors=[
            SensorSpec(
                id="capbank-protection", name="Capacitor bank unbalance & thermal monitor",
                description="Neutral unbalance CT detects failed elements; temperature and harmonic measurements protect the bank.",
                principle="Neutral CT, VT, PT100", protocol="IEC 61850", sample_interval_s=10,
                fields=[
                    num("unbalance_current", "A", 0, 5, 0.15, "Neutral unbalance current", 3),
                    num("reactive_power", "Mvar", 0, 200, 72, "Reactive power delivered", 2),
                    phases("bus_voltage", "kV", 0, 160, 132, "Bus voltage", 2),
                    num("thd_current", "%", 0, 30, 4, "Current THD", 2),
                    num("unit_case_temp", "°C", -40, 70, 32, "Capacitor unit case temperature", 1),
                    integer("failed_elements", None, 0, 12, 0, "Estimated failed elements"),
                    enum("bank_state", {"IN_SERVICE": 0.85, "OUT_OF_SERVICE": 0.14, "LOCKED_OUT": 0.01}, "Switching state"),
                ],
            ),
        ],
    ),
    Product(
        id="facts",
        name="Flexible AC Transmission Systems (FACTS)",
        group="FACTS",
        description="SVC, STATCOM (SVC Light®) and series compensation that add power and control to new or existing AC networks with minimal environmental impact.",
        url=f"{BASE}/facts",
        examples=["SVC Classic", "SVC Light® STATCOM", "Series compensation", "SVC Light Enhanced (with storage)"],
        sensors=[
            SensorSpec(
                id="facts-control", name="FACTS control & measurement",
                description="Fast control-system measurements at the point of connection.",
                principle="CT/VT with high-speed DSP control", protocol="IEC 61850 / IEC 60870-5-104", sample_interval_s=1,
                fields=[
                    num("reactive_output", "Mvar", -300, 300, 40, "Reactive power output (+cap / −ind)", 2),
                    num("bus_voltage_pu", "p.u.", 0.85, 1.15, 1.0, "Controlled bus voltage", 4),
                    num("voltage_reference_pu", "p.u.", 0.95, 1.05, 1.0, "Voltage set-point", 4),
                    num("thyristor_firing_angle", "deg", 90, 180, 130, "TCR firing angle (SVC)", 2),
                    num("response_time", "ms", 10, 60, 25, "Step response time", 1),
                    enum("control_mode", {"VOLTAGE": 0.8, "REACTIVE_POWER": 0.15, "STANDBY": 0.05}, "Control mode"),
                ],
            ),
            SensorSpec(
                id="facts-valve", name="Valve thermal & cooling sensors",
                description="Monitors thyristor/IGBT valve temperatures and the valve cooling circuit.",
                principle="PT100, conductivity cells, flow meters", protocol="Profinet / IEC 61850", sample_interval_s=10,
                fields=[
                    num("valve_temp_max", "°C", 10, 110, 55, "Hottest semiconductor position", 1),
                    num("coolant_inlet_temp", "°C", 10, 50, 32, "Coolant inlet temperature", 1),
                    num("coolant_conductivity", "µS/cm", 0, 1, 0.15, "Coolant conductivity", 3),
                    integer("redundant_levels_lost", None, 0, 4, 0, "Failed redundant valve levels"),
                ],
            ),
        ],
    ),
    Product(
        id="hvdc",
        name="High-Voltage Direct Current (HVDC)",
        group="HVDC",
        description="HVDC Classic (LCC) and HVDC Light® (VSC) systems — technology pioneered about 70 years ago — for bulk power transfer, interconnectors and offshore wind integration.",
        url=f"{BASE}/hvdc",
        examples=["HVDC Classic (LCC)", "HVDC Light® (VSC)", "UHVDC 800–1100 kV", "MACH™ control"],
        sensors=[
            SensorSpec(
                id="converter-station", name="Converter station measurement",
                description="DC-side and AC-side quantities from the MACH™ control and protection system.",
                principle="Optical DC current transducers, DC voltage dividers", protocol="IEC 61850 / IEC 60870-5-104", sample_interval_s=1,
                fields=[
                    num("dc_voltage", "kV", -800, 800, 525, "DC pole voltage", 2),
                    num("dc_current", "kA", 0, 5, 1.9, "DC pole current", 3),
                    num("active_power", "MW", -2000, 2000, 1000, "Transmitted power (+ export)", 1),
                    num("reactive_power", "Mvar", -600, 600, 50, "AC-side reactive power", 1),
                    num("firing_angle_alpha", "deg", 5, 30, 15, "Rectifier firing angle (LCC)", 2),
                    num("extinction_angle_gamma", "deg", 15, 25, 18, "Inverter extinction angle (LCC)", 2),
                    num("modulation_index", None, 0.5, 1.0, 0.85, "Modulation index (VSC)", 3),
                    enum("operating_mode", {"POWER_CONTROL": 0.85, "DC_VOLTAGE_CONTROL": 0.1, "STATCOM": 0.03, "BLOCKED": 0.02}, "Converter mode"),
                ],
            ),
            SensorSpec(
                id="valve-hall", name="Valve hall & valve monitoring",
                description="Valve temperatures, cell capacitor voltages (VSC), fire/smoke and hall climate.",
                principle="Fibre-optic valve base electronics, VESDA smoke detection", protocol="Internal fibre / IEC 61850", sample_interval_s=5,
                fields=[
                    num("cell_capacitor_voltage_avg", "kV", 1.5, 2.8, 2.2, "Average sub-module capacitor voltage (MMC)", 3),
                    num("igbt_junction_temp_max", "°C", 20, 125, 70, "Hottest IGBT junction (estimated)", 1),
                    integer("bypassed_submodules", None, 0, 20, 0, "Sub-modules in bypass"),
                    num("hall_temperature", "°C", 5, 50, 26, "Valve hall air temperature", 1),
                    num("hall_humidity", "%RH", 0, 80, 35, "Valve hall humidity", 1),
                    flag("smoke_detected", "VESDA smoke alarm", 0.0005),
                ],
            ),
            SensorSpec(
                id="dc-line", name="DC line / cable monitor",
                description="Travelling-wave fault location and cable distributed temperature sensing.",
                principle="Travelling-wave sensors, DTS on fibre", protocol="IEC 61850", sample_interval_s=60,
                fields=[
                    num("cable_max_temp", "°C", 0, 90, 45, "Maximum conductor temperature (DTS)", 1),
                    num("hotspot_location_km", "km", 0, 600, 120, "Location of hottest point", 2),
                    flag("dc_line_fault", "DC line fault detected", 0.0005),
                    num("fault_location_km", "km", 0, 600, 0, "Last fault distance from station", 2),
                ],
            ),
        ],
    ),
    Product(
        id="cooling-systems",
        name="Cooling Systems",
        group="Cooling Systems",
        description="Energy-efficient pure (deionized) water cooling systems for HVDC/FACTS valves, drives and industrial power electronics.",
        url=f"{BASE}/cooling-systems",
        examples=["Valve cooling", "Drive cooling", "Dry / wet coolers"],
        sensors=[
            SensorSpec(
                id="pure-water-loop", name="Pure-water cooling loop sensors",
                description="Instruments on the primary deionized-water loop and pumps.",
                principle="PT100, conductivity cell, magnetic flow meter, pressure transmitters", protocol="Profinet / Modbus TCP", sample_interval_s=10,
                fields=[
                    num("inlet_temp", "°C", 10, 55, 35, "Coolant temperature into load", 2),
                    num("outlet_temp", "°C", 10, 70, 45, "Coolant temperature from load", 2),
                    num("flow_rate", "l/s", 0, 50, 22, "Coolant flow", 2),
                    num("pressure", "bar", 0, 12, 6, "Loop pressure", 2),
                    num("conductivity", "µS/cm", 0, 2, 0.2, "Water conductivity", 3),
                    num("dissolved_oxygen", "ppb", 0, 500, 50, "Dissolved oxygen", 1),
                    num("pump_vibration", "mm/s", 0, 15, 1.5, "Pump vibration velocity", 2),
                    enum("active_pump", {"P1": 0.5, "P2": 0.5}, "Duty pump"),
                    flag("leak_detected", "Leakage detected", 0.0005),
                ],
            ),
            SensorSpec(
                id="heat-exchanger", name="Outdoor cooler sensors",
                description="Fan speeds and air temperatures on dry coolers.",
                principle="VFD feedback, PT100", protocol="Modbus TCP", sample_interval_s=30,
                fields=[
                    num("air_inlet_temp", "°C", -40, 50, 18, "Air inlet temperature", 1),
                    num("fan_speed", "%", 0, 100, 55, "Fan speed command", 1),
                    num("heat_rejected", "kW", 0, 20000, 6500, "Heat rejected", 0),
                ],
            ),
        ],
    ),
    Product(
        id="energy-storage",
        name="Energy Storage (BESS)",
        group="Energy Storage",
        description="Battery energy storage systems that support renewable integration and grid stability — e.g. on the island grid of Porto Santo.",
        url=f"{BASE}/energystorage",
        examples=["e-mesh™ PowerStore™", "Containerised BESS"],
        sensors=[
            SensorSpec(
                id="bms-rack", name="Battery management system (rack level)",
                description="Cell voltages, temperatures, state of charge and health aggregated per rack.",
                principle="BMS cell monitoring ASICs, NTC thermistors, Hall current sensor", protocol="Modbus TCP / CAN", sample_interval_s=5,
                fields=[
                    num("state_of_charge", "%", 0, 100, 62, "State of charge", 1),
                    num("state_of_health", "%", 60, 100, 96, "State of health", 1),
                    num("rack_voltage", "V", 600, 1500, 1200, "Rack DC voltage", 1),
                    num("rack_current", "A", -400, 400, 80, "Rack current (+ discharge)", 1),
                    num("cell_voltage_max", "V", 2.8, 3.65, 3.33, "Highest cell voltage (LFP)", 3),
                    num("cell_voltage_min", "V", 2.5, 3.6, 3.29, "Lowest cell voltage (LFP)", 3),
                    num("cell_temp_max", "°C", -20, 60, 29, "Highest cell temperature", 1),
                    num("cell_temp_min", "°C", -20, 60, 24, "Lowest cell temperature", 1),
                    counter("cycle_count", "cycles", 400, 10000, 1, "Equivalent full cycles"),
                    enum("bms_state", {"IDLE": 0.2, "CHARGING": 0.35, "DISCHARGING": 0.42, "FAULT": 0.01, "MAINTENANCE": 0.02}, "BMS state"),
                ],
            ),
            SensorSpec(
                id="bess-safety", name="Container environment & safety",
                description="HVAC, off-gas and fire detection inside the battery enclosure.",
                principle="Electrochemical gas sensors, smoke detectors, HVAC controller", protocol="Modbus TCP", sample_interval_s=10,
                fields=[
                    num("container_temp", "°C", -20, 50, 23, "Container air temperature", 1),
                    num("container_humidity", "%RH", 0, 95, 40, "Container humidity", 1),
                    num("h2_concentration", "ppm", 0, 1000, 0, "Hydrogen off-gas", 1),
                    num("co_concentration", "ppm", 0, 500, 0, "Carbon monoxide", 1),
                    flag("smoke_alarm", "Smoke detected", 0.0005),
                    flag("door_open", "Container door open", 0.005),
                    enum("fire_suppression_state", {"ARMED": 0.995, "DISCHARGED": 0.001, "FAULT": 0.004}, "Suppression system state"),
                ],
            ),
        ],
    ),
    Product(
        id="power-conversion",
        name="Power Conversion Solutions",
        group="Power Conversion",
        description="Power conversion stations (inverters/PCS) for grid-friendly energy storage, solar and renewable integration.",
        url=f"{BASE}/power-conversion",
        examples=["PCS100 ESS", "Grid-forming converters"],
        sensors=[
            SensorSpec(
                id="pcs-inverter", name="Inverter / PCS telemetry",
                description="Converter AC and DC quantities, efficiency and semiconductor temperatures.",
                principle="Internal converter controller measurements", protocol="Modbus TCP / SunSpec", sample_interval_s=1,
                fields=[
                    num("ac_active_power", "kW", -4000, 4000, 1500, "AC active power (+ export)", 1),
                    num("ac_reactive_power", "kvar", -2000, 2000, 0, "AC reactive power", 1),
                    num("dc_link_voltage", "V", 600, 1500, 1100, "DC link voltage", 1),
                    num("dc_current", "A", -3000, 3000, 1300, "DC current", 1),
                    num("grid_frequency", "Hz", 49.5, 50.5, 50.0, "Grid frequency", 3),
                    num("efficiency", "%", 90, 99.5, 98.4, "Conversion efficiency", 2),
                    num("heatsink_temp", "°C", 0, 100, 48, "Heat-sink temperature", 1),
                    enum("grid_mode", {"GRID_FOLLOWING": 0.75, "GRID_FORMING": 0.2, "STANDBY": 0.05}, "Control mode"),
                ],
            ),
        ],
    ),
    Product(
        id="static-frequency-converter",
        name="Static Frequency Converters",
        group="Static Frequency Converters",
        description="Converters that connect industrial, utility and railway systems with different voltages and frequencies (e.g. 50 Hz ↔ 16.7 Hz rail).",
        url=f"{BASE}/static-frequency-converters-sfc",
        examples=["Railway intertie SFC", "Generator start-up SFC"],
        sensors=[
            SensorSpec(
                id="sfc-telemetry", name="SFC converter telemetry",
                description="Input and output side electrical quantities and converter temperature.",
                principle="Converter control measurements", protocol="IEC 61850", sample_interval_s=1,
                fields=[
                    num("input_frequency", "Hz", 49.5, 50.5, 50.0, "Utility side frequency", 3),
                    num("output_frequency", "Hz", 16.5, 16.9, 16.7, "Rail side frequency", 3),
                    num("input_power", "MW", 0, 120, 60, "Input power", 2),
                    num("output_voltage", "kV", 0, 20, 15, "Output voltage", 2),
                    num("converter_temp", "°C", 10, 90, 45, "Converter coolant temperature", 1),
                ],
            ),
        ],
    ),
    Product(
        id="power-semiconductors",
        name="Power Semiconductors",
        group="Power Semiconductors",
        description="IGBT, IGCT, thyristor and diode press-pack and module devices for HVDC, wind, rail and e-mobility.",
        url=f"{BASE}/semiconductors",
        examples=["HiPak IGBT modules", "StakPak press-pack IGBT", "IGCT", "Phase-control thyristors", "RoadPak"],
        sensors=[
            SensorSpec(
                id="igbt-module", name="IGBT module condition sensors",
                description="Gate-driver-level measurements used for junction temperature estimation and lifetime prediction.",
                principle="NTC thermistor, Vce(on) sensing in gate driver", protocol="Fibre-optic gate driver link", sample_interval_s=1,
                fields=[
                    num("junction_temp_virtual", "°C", -40, 175, 85, "Virtual junction temperature Tvj", 1),
                    num("case_temp", "°C", -40, 125, 60, "Baseplate / case temperature", 1),
                    num("vce_on", "V", 1.0, 4.0, 1.9, "Collector-emitter on-state voltage", 3),
                    num("collector_current", "A", 0, 3600, 1200, "Collector current", 1),
                    num("switching_frequency", "Hz", 100, 20000, 2500, "Switching frequency", 0),
                    counter("thermal_cycles", "cycles", 100000, 10000000, 3, "Counted power cycles (ΔTj > 20 K)"),
                    enum("gate_driver_status", {"OK": 0.995, "DESAT_FAULT": 0.002, "UVLO": 0.003}, "Gate driver status"),
                ],
            ),
        ],
    ),
    # ------------------------------------------------------------------ Automation & comms
    Product(
        id="substation-automation",
        name="Substation Automation, Protection & Control",
        group="Automation, Protection and Control",
        description="IEDs, process interface units/merging units, RTUs, SCADA and DMS for grid and substation automation, protection and control.",
        url=f"{BASE}/substation-automation-protection-and-control",
        examples=["Relion® protection relays", "SAM600 merging unit", "RTU500 series", "MicroSCADA X"],
        sensors=[
            SensorSpec(
                id="protection-ied", name="Protection relay (IED) measurements",
                description="Feeder/line measurements and protection events from a Relion® class IED.",
                principle="CT/VT analogue inputs, digital signal processing", protocol="IEC 61850 MMS / GOOSE", sample_interval_s=1,
                fields=[
                    phases("phase_current", "A", 0, 2000, 400, "Phase current", 1),
                    phases("phase_voltage", "kV", 0, 80, 66.4, "Phase-to-earth voltage", 2),
                    num("active_power", "MW", -200, 200, 75, "Active power", 2),
                    num("power_factor", None, 0.5, 1.0, 0.96, "Power factor", 3),
                    num("frequency", "Hz", 49.5, 50.5, 50.0, "Frequency", 3),
                    enum("last_protection_event", {"NONE": 0.97, "OVERCURRENT_51": 0.01, "EARTH_FAULT_51N": 0.008, "DISTANCE_21_Z1": 0.006, "DIFFERENTIAL_87": 0.003, "UNDERFREQ_81U": 0.003}, "Last protection function operated (ANSI code)"),
                    num("fault_distance", "km", 0, 100, 0, "Fault locator distance", 2),
                ],
            ),
            SensorSpec(
                id="ied-health", name="IED / merging unit self-supervision",
                description="Device health, time synchronisation and communication performance.",
                principle="Internal diagnostics", protocol="IEC 61850 / SNMP", sample_interval_s=10,
                fields=[
                    num("ptp_time_offset", "ns", -1000, 1000, 50, "IEEE 1588 PTP offset from grandmaster", 0),
                    num("goose_latency", "ms", 0, 10, 1.2, "GOOSE transfer time", 3),
                    integer("sv_lost_samples", None, 0, 100, 0, "Sampled-values frames lost"),
                    num("cpu_load", "%", 0, 100, 22, "CPU load", 1),
                    num("internal_temp", "°C", -25, 85, 42, "Internal temperature", 1),
                    enum("health", {"OK": 0.98, "WARNING": 0.017, "ALARM": 0.003}, "Self-supervision state"),
                ],
            ),
        ],
    ),
    Product(
        id="communication-networks",
        name="Communication Networks",
        group="Communication Networks",
        description="Reliable wired and 5G-enabled wireless communication networks for utilities, mining, oil & gas and transportation.",
        url=f"{BASE}/communication-networks",
        examples=["FOX615 multiplexer", "TROPOS wireless mesh", "XMC20", "Private LTE/5G"],
        sensors=[
            SensorSpec(
                id="network-node", name="Network node telemetry",
                description="Radio and link KPIs collected from each mesh router / multiplexer.",
                principle="Device telemetry", protocol="SNMP / NETCONF", sample_interval_s=30,
                fields=[
                    num("rssi", "dBm", -110, -30, -65, "Received signal strength", 1),
                    num("snr", "dB", 0, 40, 25, "Signal-to-noise ratio", 1),
                    num("latency", "ms", 0, 200, 8, "Round-trip latency", 2),
                    num("packet_loss", "%", 0, 10, 0.05, "Packet loss", 3),
                    num("throughput", "Mbps", 0, 1000, 120, "Link throughput", 1),
                    enum("link_status", {"UP": 0.99, "DEGRADED": 0.008, "DOWN": 0.002}, "Link status"),
                    counter("uptime", "s", 1000000, 999999999, 30, "Device uptime"),
                ],
            ),
        ],
    ),
    Product(
        id="cable-accessories",
        name="Cable Accessories",
        group="Cable Accessories",
        description="Connectors, terminations and joints for 12–145 kV cable applications.",
        url=f"{BASE}/cable-accessories-and-connectors",
        examples=["Cable terminations", "Cable joints", "Separable connectors"],
        sensors=[
            SensorSpec(
                id="joint-monitor", name="Cable joint / termination monitor",
                description="Partial discharge, temperature and sheath current at joints and terminations.",
                principle="HFCT, surface temperature sensor, sheath CT", protocol="LoRaWAN / Modbus", sample_interval_s=300,
                fields=[
                    num("pd_magnitude", "pC", 0, 2000, 10, "Partial discharge magnitude", 1),
                    num("joint_temp", "°C", -20, 110, 40, "Joint surface temperature", 1),
                    num("sheath_current", "A", 0, 200, 8, "Sheath circulating current", 2),
                    num("conductor_current", "A", 0, 1500, 500, "Conductor load current", 1),
                    flag("water_ingress", "Moisture ingress detected", 0.001),
                ],
            ),
        ],
    ),
    Product(
        id="substations",
        name="Substations & Electrification",
        group="Substations & Electrification",
        description="Turnkey substations, eHouses and electrification solutions integrating power from conventional and renewable generation.",
        url=f"{BASE}/substations",
        examples=["AIS/GIS substations", "Modular eHouse", "Offshore substations"],
        sensors=[
            SensorSpec(
                id="substation-environment", name="Substation environment & auxiliary supply",
                description="Building climate, DC battery system and physical security.",
                principle="Environmental sensors, battery monitor, door contacts", protocol="IEC 61850 / Modbus", sample_interval_s=60,
                fields=[
                    num("room_temp", "°C", -10, 50, 22, "Control room temperature", 1),
                    num("room_humidity", "%RH", 0, 100, 40, "Control room humidity", 1),
                    num("dc_battery_voltage", "V", 100, 140, 125, "Station 110 V DC battery voltage", 2),
                    num("battery_charger_current", "A", 0, 100, 4, "Charger current", 2),
                    flag("ac_aux_supply_lost", "Loss of auxiliary AC supply", 0.001),
                    flag("intrusion_alarm", "Perimeter / door intrusion", 0.002),
                    flag("flood_detected", "Water on floor", 0.0005),
                ],
            ),
        ],
    ),
    Product(
        id="grid-emotion",
        name="Grid-eMotion® (EV fleet charging)",
        group="Grid-eMotion",
        description="Grid-eMotion® Fleet charging infrastructure for e-buses and trucks with flexible utility grid connection and power-quality compliance.",
        url="https://www.hitachienergy.com/offering",
        examples=["Grid-eMotion® Fleet", "Grid-eMotion® Flash"],
        sensors=[
            SensorSpec(
                id="charger-session", name="Charging point telemetry",
                description="Per-connector session data and grid-side measurements.",
                principle="Charger controller + revenue meter", protocol="OCPP 2.0.1", sample_interval_s=15,
                fields=[
                    num("charging_power", "kW", 0, 600, 150, "Charging power", 1),
                    num("session_energy", "kWh", 0, 600, 85, "Energy delivered this session", 2),
                    num("vehicle_soc", "%", 0, 100, 55, "Vehicle state of charge", 1),
                    num("connector_temp", "°C", -20, 90, 38, "Connector / pantograph temperature", 1),
                    num("grid_power_factor", None, 0.8, 1.0, 0.99, "Grid-side power factor", 3),
                    enum("connector_status", {"AVAILABLE": 0.35, "CHARGING": 0.55, "FINISHING": 0.05, "FAULTED": 0.01, "RESERVED": 0.04}, "OCPP connector status"),
                ],
            ),
        ],
    ),
    Product(
        id="power-quality",
        name="Power Quality",
        group="Power Quality",
        description="Products, systems and consulting that keep voltage and current waveforms clean for utilities and industry.",
        url=f"{BASE}/power-quality",
        examples=["PCS100 AVC voltage conditioner", "Active filters", "PQ analysers"],
        sensors=[
            SensorSpec(
                id="pq-analyser", name="Power-quality analyser (IEC 61000-4-30 Class A)",
                description="Harmonics, flicker, unbalance and voltage events at the point of common coupling.",
                principle="Class A PQ meter", protocol="IEC 61850 / PQDIF", sample_interval_s=600,
                fields=[
                    phases("voltage_thd", "%", 0, 12, 2.2, "Voltage THD per phase", 2),
                    phases("current_thd", "%", 0, 40, 6, "Current THD per phase", 2),
                    num("flicker_pst", None, 0, 5, 0.4, "Short-term flicker severity", 3),
                    num("flicker_plt", None, 0, 5, 0.35, "Long-term flicker severity", 3),
                    num("voltage_unbalance", "%", 0, 5, 0.6, "Negative-sequence unbalance", 2),
                    num("frequency", "Hz", 49.5, 50.5, 50.0, "Frequency", 3),
                    enum("last_event", {"NONE": 0.95, "SAG": 0.03, "SWELL": 0.01, "INTERRUPTION": 0.005, "TRANSIENT": 0.005}, "Last voltage event"),
                ],
            ),
        ],
    ),
]

# Common envelope fields attached to every reading
ENVELOPE_FIELDS = [
    {"name": "timestamp", "json_type": "string (ISO-8601 UTC)", "description": "Sample time"},
    {"name": "asset_id", "json_type": "string", "description": "Unique asset identifier, e.g. HE-TX-0001"},
    {"name": "sensor_id", "json_type": "string", "description": "Sensor type id"},
    {"name": "sequence", "json_type": "integer", "description": "Monotonic sample number"},
    {"name": "quality", "json_type": "string (enum)", "description": "GOOD | UNCERTAIN | BAD (IEC 61850 style quality)"},
]

_INDEX = {p.id: p for p in PRODUCTS}


def get_product(product_id: str) -> Product | None:
    return _INDEX.get(product_id)


def get_sensor(product_id: str, sensor_id: str):
    p = get_product(product_id)
    if not p:
        return None, None
    return p, next((s for s in p.sensors if s.id == sensor_id), None)
