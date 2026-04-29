"""Physical constants, unit conversions, and engineering defaults.

All values match the CMA Lift Station Calculations Template defaults.
Reference: Parameters_needed_for_Pump_Lift_Station_Design.pdf, CMA, Maitland FL.
"""

from __future__ import annotations

# --- Physical constants ----------------------------------------------------

#: Acceleration due to gravity (ft/s^2). Matches spreadsheet TDH!D9.
GRAVITY_FT_S2: float = 32.2

#: Density of water at 60 deg F (lb/ft^3). Matches spreadsheet TDH!D7.
WATER_DENSITY_LB_FT3: float = 62.37

#: Kinematic viscosity of water at 60 deg F (ft^2/sec). Matches spreadsheet
#: TDH!D8 (the spreadsheet shows 1.22E-05 but stores 1.217E-05).
WATER_KINEMATIC_VISC_FT2_SEC: float = 1.217e-5

# --- Unit conversions -------------------------------------------------------

#: Cubic feet per gallon. Used for pipe area / GPM -> ft/s velocity conversion.
#: 1 ft^3 = 7.48051948 gal, so 1 gal/min over 1 ft^2 area = (1/7.4805) / 60
#: ft/s = 1/448.831 ft/s. The spreadsheet uses 448.831 directly.
GPM_TO_CFS_DIVISOR: float = 448.831

#: Gallons per cubic foot. Used for wetwell volume calc (V = pi*D^2/4 * h * 7.48).
#: NOTE: Spreadsheet uses 7.48 (truncated). True value is 7.48051948.
#: We match the spreadsheet for regression-test parity.
GAL_PER_FT3: float = 7.48

#: Conversion factor from psi to feet of water column.
#: 1 psi = 2.31 ft of water (at 60 deg F). Spreadsheet hardcodes 2.31 in
#: Headloss Fitting!D11 (=11.9*2.31).
PSI_TO_FT_OF_WATER: float = 2.31

#: Inches per foot.
INCHES_PER_FOOT: float = 12.0

# --- Hazen-Williams defaults ------------------------------------------------

#: Default Hazen-Williams C-factor for ductile iron pipe (DIP).
#: Matches spreadsheet TDH!D10 default.
HAZEN_WILLIAMS_C_DIP: float = 120.0

#: Hazen-Williams head-loss equation coefficient (US customary units).
#: hf = COEFF * L * (100/C)^1.85 * Q^1.85 / D^4.8655
#: where Q = GPM, D = inches, L = ft, hf = ft.
#: Spreadsheet uses 0.002083; published value is 0.002083.
HAZEN_WILLIAMS_COEFF_US: float = 0.002083

# --- Population / flow defaults --------------------------------------------

#: Default persons per residential unit (Ten States Standards / FAC 64E-6).
#: Spreadsheet Flow Rate!C18 multiplies parcel count by 2.5.
PERSONS_PER_RESIDENTIAL_UNIT: float = 2.5

#: Gallons per capita per day (Ten States Standards 11.243.a default).
#: Used as a fallback when per-unit Table I values aren't applicable.
GPCD_TEN_STATES_DEFAULT: float = 100.0

#: Minimum peak factor floor (per spreadsheet Flow Rate!C21 IF(...,2.5,...)).
PEAK_FACTOR_FLOOR: float = 2.5
