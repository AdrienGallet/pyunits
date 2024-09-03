"""
Property class, to be universally used accross all pyECD variables if possible.

To be used to print units, convert them, etc.

Need to take a closer look at this and see how the performance can be improved.

Future tasks:
- Think about how to implement a simple yet effective unit converter to both SI and imperial units for lengths, areas , resistance values, etc.
- Remember that the focus is on practicality at the expense of consistency
--- Hence, allow the use of N, Pa, etc., and make conversions for the most common used formats.
--- For lengths, include: mm, cm, m
--- For areas, include: mm2, cm2, m2.
--- For section modulus: mm3, cm3, m3
--- For moments of inertia: mm4, cm4, m4
--- For force, include: N, kN, MN, etc.
--- For stress, include: N/mm2 (=MPa), Pa, MPa
--- For moments, include: Nm, kNm, Nmm, Ncm, MNm
- Provide imperial units


#------------ FUTURE FEATURES ------------#
- Provide comparison operators (greater than, less than, and/or equal to)
- Provide the equality operator
- Provide a full info print function

- Create private or protected members so that things don't get changed carelessly.
- Consider the time complexity of convert() being O(2n) right now, which could be improved to (n). This could be alleviated, by creating a dictionary of a dictionary for unitDict, and using hash look-ups (as opposed to linear search look ups)
- Improve the formula description, so that formulas can more easily be back-tracked. This will require using parenthesis, and doing some clean-up after a certain set of operations has been completed.
- When adding, subtracting, multiplying, dividing, provide a feature that is "smartly" selects the unit, instead of always converting everything to the base unit. For example, this could be achieved by recording what units were used initially, and then conducting some sort of similarity search.
- When creating the tmpName and formula, consider providing paranethesis logic in case mult/div gets combined with add/sub
- Allow the "baseUnit" to be changed, which will have an impact on how mult/div operations are conducted. By this, we mean to allow a user to change the default unit from "m" to "mm" for example. This could be provided through a settings menu, which would also provide access to changing the unitDit, the precision level, etc.
- Consider implementing the decimal package
--- This is especially important, because right now I am simply relying on the round function, which may not in fact be perfectly accurate. Properly understanding floating point values, and making sure that a great deal of precision is provided is preferrable.

Look into this class further.
"""

# Modules
import copy
import re

"""
#Global variables
#-----------------------------------------------------------------------#
Define all the unitSets (length, area, force, etc.) and the associated linked units
- this is a highly controlled data-structure, do not change the order carelessly
- Each value entry is a list of the following format:
--- [list of supported units,
	 conversion factor relative to "Norm" unit,
	 "Norm" unit, SI composition list in [length {L}, mass {M}, time {T}, temperature {H}, electric current {E}, amount of substance {A}, luminous intensity {I}]
	]
- unitSets must have mutually exclusive units
"""
unitDict = {
    "unitless": [[""], [], "", [0, 0, 0, 0, 0, 0, 0]],
    "length": [
        ["μm", "mm", "cm", "dm", "m", "km"],
        [1e6, 1e3, 1e2, 1e1, 1, 1e-3],
        "m",
        [1, 0, 0, 0, 0, 0, 0],
    ],
    "area": [
        ["μm2", "mm2", "cm2", "dm2", "m2", "km2"],
        [1e12, 1e6, 1e4, 1e2, 1, 1e-6],
        "m2",
        [2, 0, 0, 0, 0, 0, 0],
    ],
    "section mod.|volume": [
        ["μm3", "mm3", "cm3", "dm3", "m3", "km3"],
        [1e18, 1e9, 1e6, 1e3, 1, 1e-9],
        "m3",
        [3, 0, 0, 0, 0, 0, 0],
    ],
    "mom. of inert.|tors. const.": [
        ["μm4", "mm4", "cm4", "dm4", "m4", "km4"],
        [1e24, 1e12, 1e8, 1e4, 1, 1e-12],
        "m4",
        [4, 0, 0, 0, 0, 0, 0],
    ],
    "wraping constant": [
        ["μm6", "mm6", "cm6", "dm6", "m6", "km6"],
        [1e36, 1e18, 1e12, 1e6, 1, 1e-18],
        "m6",
        [6, 0, 0, 0, 0, 0, 0],
    ],
    "mass": [["g", "kg"], [1e3, 1], "kg", [0, 1, 0, 0, 0, 0, 0]],
    "time": [["μs", "ms", "s", "ks"], [1e6, 1e3, 1, 1e-3], "s", [0, 0, 1, 0, 0, 0, 0]],
    "force": [["N", "kN", "MN"], [1, 1e-3, 1e-6], "N", [1, 1, -2, 0, 0, 0, 0]],
    "moment": [["Nm", "kNm", "MNm"], [1, 1e-3, 1e-6], "Nm", [2, 1, -2, 0, 0, 0, 0]],
    "stress|strain": [
        ["Pa", "kPa", "MPa", "N/mm2"],
        [1, 1e-3, 1e-6, 1e-6],
        "Pa",
        [-1, 1, -2, 0, 0, 0, 0],
    ],
}
precLevel = 15  # Level of precision for mult/div operations
# -----------------------------------------------------------------------#


# Physical variable class - made to deal with physical measurements
class pyunits:
    # --- Class constructor
    def __init__(self, name, value=None, unit=None, SIID=None, info=None, formula=None):
        # pytCheck input is sufficient
        if name != None and value != None and unit != None:
            self.name = name  # Variable name
            self.value = round(value, precLevel)  # Variable value
            self.unit = unit  # Variable unit

        elif value == None and unit == None:
            # Check if name string contains input variables
            orgName = name  # Save the name to a seperate variable
            orgName.replace(" ", "")  # Remove any whitespace from the input
            nameSplit = orgName.split("=")  # Split the name

            # If length does not equal to 2, then:
            if len(nameSplit) < 2:  # Missing equal sign
                raise Exception("pyunits() declaration missing an equal [=] sign.")
            elif len(nameSplit) > 2:  # Multiple equal signs
                raise Exception(
                    "pyunits() declaration has more than one equal [=] sign."
                )
            else:  # Continue to extract pyunits
                self.name = nameSplit[0]  # Retrieve the name
                tmpOut = re.search(
                    r"[^0-9|^.]", nameSplit[1]
                )  # Evaluate position of first unit character
                value, unit = (
                    nameSplit[1][: tmpOut.start()],
                    nameSplit[1][tmpOut.start() :],
                )  # Split the string at that location
                if "." in value:  # If the value is a decimal, convert to float
                    self.value = round(float(value), precLevel)  # Variable value
                else:  # Otherwise, convert to an integer
                    self.value = int(value)
                self.unit = unit  # Variable unit
        elif (value == None and unit != None) or (value != None and unit == None):
            raise Exception(
                "missing input, need to specify variable name, value and unit. Ex: pyunits('a=10m') or pyunits('a', '10', 'm'))."
            )
        else:
            raise Exception("input to pyunits() not valid.")

        # Assign other class variables
        self.SIID = SIID  # SI units IDdentifier
        self.info = info  # Description of variable
        self.formula = formula  # Formula of variable if available

        # --- Establish what unitSet we are dealing with ---
        self.unitSet = None  # Default value in case of error or unknown unitSet
        lstUnitSet = pyunits.findUnitSet(self.unit)  # Create lstUnitSet

        # If list is 0 length, then an unknown unitSet was created (can occur due to multiplication/division of variables).
        if len(lstUnitSet) == 0:  # Unknown unitSet
            # Check that SIID is provided, otherwise raise an exception
            if self.SIID == None:
                raise Exception(
                    "unknown units, SIID must be specified within pyunits call."
                )
            # Assume that if a non-unitSet variable is used, all units are in their "base" form already
            self.unitBase = self.unit
            self.valueBase = round(self.value, precLevel)
        else:  # List has length 1, which contains the unitSet
            self.unitSet = lstUnitSet[0]  # Assign the unitSet
            self.SIID = unitDict[self.unitSet][3]  # Assign SIID
            self.unitBase = unitDict[self.unitSet][2]  # Assign base unit
            # --- Convert and save value in baseUnits
            if self.unitBase == self.unit:
                self.valueBase = self.value
            else:
                self.valueBase = round(
                    self.convert(self.unitBase, out="value"), precLevel
                )

    # --- A dunder method to change what is shown with print()
    def __repr__(self):
        rString = (
            "pyunits('{}', value={}, unit='{}', SIID={}, info={}, formula={})".format(
                self.name, self.value, self.unit, self.SIID, self.info, self.formula
            )
        )
        return rString

    def __str__(self):
        return "{} = {}{}".format(self.name, self.value, self.unit)

    # --- Addition magic  method for arithmetics
    def __add__(self, other):
        # If "other" is not pyunits, then treat the "other" value as a number of the same units. Hence, simply update the values
        if not isinstance(other, pyunits):
            newpyunits = copy.deepcopy(self)  # Required to return a new variable
            # Update value and base values
            newpyunits.value = round(self.value + other, precLevel)
            if newpyunits.unitBase == self.unit:
                newpyunits.valueBase = round(self.valueBase + other, precLevel)
            else:
                newpyunits.valueBase = round(
                    self.valueBase
                    + pyunits("tmp", other, self.unit).convert(
                        self.unitBase, out="value"
                    ),
                    precLevel,
                )
            return newpyunits  # Return the object itself

        # If adding accross different unit sets, raise exception (bc it is non-phyisical to add different unitSets together).
        if self.SIID != other.SIID:
            raise Exception(
                "cannot add/subtract values from different unitSets. Unit sets in question: {} and {} | SIID: {} and {}.".format(
                    self.unitSet, other.unitSet, self.SIID, other.SIID
                )
            )

        # Otherwise, perform addition operation
        tmpName = self.name + "+" + other.name  # Create a new name
        # Check if the unitSet exists within unitDict
        lstUnitSet = pyunits.findUnitSet(self.unit)
        if len(lstUnitSet) == 0:  # unit does not exist within unitSets
            return pyunits(
                tmpName,
                round(self.valueBase + other.valueBase, precLevel),
                self.unitBase,
                SIID=self.SIID,
                formula=tmpName,
            )  # Return new pyunits
        else:  # List has length 1, meaning unitSet exists
            return pyunits(
                tmpName,
                round(self.valueBase + other.valueBase, precLevel),
                self.unitBase,
                formula=tmpName,
            )  # Return new pyunits

    # --- Subtraction magic, method for arithmetics
    def __sub__(self, other):  # Does negated addition
        # If "other" is not a pyunits (assuming it is a number)
        if not isinstance(other, pyunits):
            return self.__add__(-other)

        # If it is a pyunits, make the appropriate changes to the "other" pyunits, and then perform addition of it's negative value
        else:
            # Required in order not make references changes to variable "other"
            other = copy.deepcopy(other)

            # Then conduct operation
            other.value *= -1
            other.valueBase *= -1  # Negate values
            newpyunits = self.__add__(other)  # Conduct negative addition

            # Update the name and formula to reflect true operation
            tmpName = self.name + "-" + other.name
            newpyunits.name = tmpName
            newpyunits.formula = tmpName
            return newpyunits  # Return physical variable

    # --- Multiplication magic, method for arithmetics
    def __mul__(self, other):
        # If "other" is not pyunits, then assume "other" is a number to manipulate the "self" variable. Update both value and baseValue
        if not isinstance(other, pyunits):
            newpyunits = copy.deepcopy(self)  # Required in order not to change self
            newpyunits.value = round(self.value * other, precLevel)  # Update the value
            newpyunits.valueBase = round(
                self.valueBase * other, precLevel
            )  # Update the SI value (no conversion needed)
            return newpyunits  # Return the object itself

        # Otherwise perform multiplication operation
        tmpName = self.name + "*" + other.name  # Create a new name

        # Identify the new SIID
        newSIID = [sum(i) for i in zip(self.SIID, other.SIID)]

        # Check if the unitSet exists within unitDict
        lstUnitSet = pyunits.findUnitSet(newSIID)
        if len(lstUnitSet) == 0:  # unitSet does not exist
            tmpUnit = pyunits.findUnitFromSIID(
                newSIID
            )  # Find the correct unit from SIID

            # Conduct operation
            return pyunits(
                tmpName,
                round(self.valueBase * other.valueBase, precLevel),
                tmpUnit,
                SIID=newSIID,
                formula=tmpName,
            )

        # Only other option is that len(lstUnitSet) == 1, the unitSet exists
        else:
            tmpUnit = unitDict[lstUnitSet[0]][2]  # Assign unit name

            # Conduct operation
            return pyunits(
                tmpName,
                round(self.valueBase * other.valueBase, precLevel),
                tmpUnit,
                formula=tmpName,
            )

    # --- Division magic, method for arithmetics
    def __truediv__(self, other):
        # If "other" is not a pyunits (assuming it is a number)
        if not isinstance(other, pyunits):
            return self.__mul__(1 / other)

        # If it is a pyunits, make the appropriate changes to the "other" pyunits
        else:
            # Deepcopy required to make changes to "other" variable
            other = copy.deepcopy(other)

            # Then conduct operation
            other.value = 1 / other.value
            other.valueBase = 1 / other.valueBase  # Invert values
            other.SIID = [i * -1 for i in other.SIID]
            newpyunits = self.__mul__(other)  # Conduct inverted multiplication

            # Update the name and formula to reflect true operation
            tmpName = self.name + "/" + other.name
            newpyunits.name = tmpName
            newpyunits.formula = tmpName
            return newpyunits  # Return physical variable

    # --- Power magic, method for arithmetics
    def __pow__(self, other, mod=None):
        # If exp is not a number, raise an exception:
        if type(other) != int and type(other) != float:
            raise Exception("exponent must be an integer or float.")

        # Calculate the correct value
        tmpValueBase = round(self.valueBase**other, precLevel)  # Use base

        # Adjust the SIID based on the power
        tmpSIID = [round(i * other, precLevel) for i in self.SIID]

        # Check if the unitSet exists within unitDict
        lstUnitSet = pyunits.findUnitSet(tmpSIID)
        if len(lstUnitSet) == 0:  # unitSet does not exist
            tmpUnitBase = pyunits.findUnitFromSIID(tmpSIID)  # Find the correct unit
        else:  # Only other option is that len(lstUnitSet) == 1, the unitSet exists
            tmpUnitBase = unitDict[lstUnitSet[0]][2]  # Assign unit name

        tmpName = self.name + "^" + str(other)  # Create a new name

        return pyunits(
            tmpName, tmpValueBase, tmpUnitBase, SIID=tmpSIID, formula=tmpName
        )

    # --- For reverse addition, subtraction, multiplication and division
    def __radd__(self, other):
        return self.__add__(other)

    def __rsub__(self, other):
        return self.__sub__(other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __rtruediv__(self, other):  # Needs adjustment b/c division is not commutative
        # Invert values and SIID of self
        newSelf = copy.deepcopy(self)  # Deepcopy dissociated from self
        newSelf.value = 1 / newSelf.value
        newSelf.valueBase = 1 / newSelf.valueBase
        newSelf.SIID = [i * -1 for i in newSelf.SIID]

        # Convert other into pyunits (otherwise SIID is not updated)
        other = pyunits(str(other), other, "")
        newpyunits = newSelf.__mul__(other)  # Conduct inverted multiplication

        # Update the name and formula to reflect true operation
        tmpName = other.name + "/" + newSelf.name
        newpyunits.name = tmpName
        newpyunits.formula = tmpName
        return newpyunits  # Return physical variable

    # --- Unary arithemtic, negative
    def __neg__(self):
        newpyunits = copy.deepcopy(self)
        newpyunits.value *= -1
        newpyunits.valueBase *= -1
        return newpyunits

    # --- Unary arithemtic, absolute
    def __abs__(self):
        newpyunits = copy.deepcopy(self)
        newpyunits.value = abs(newpyunits.value)
        newpyunits.valueBase = abs(newpyunits.valueBase)
        return newpyunits

    # --- Comparison magic, less than
    def __lt__(self, other):
        if not isinstance(other, pyunits):
            return round(self.value, precLevel) < round(other, precLevel)

        # Ensure variables are the same SIID
        pyunits.checkSameSIIDCompare(self, other)

        # If no errors, then conduct comparison
        return round(self.valueBase, precLevel) < round(other.valueBase, precLevel)

    # --- Comparison magic, greater than
    def __gt__(self, other):
        if not isinstance(other, pyunits):
            return round(self.value, precLevel) > round(other, precLevel)

        # Ensure variables are the same SIID
        pyunits.checkSameSIIDCompare(self, other)

        # If no errors, then conduct comparison
        return round(self.valueBase, precLevel) > round(other.valueBase, precLevel)

    # --- Comparison magic, less than or equal
    def __le__(self, other):
        if not isinstance(other, pyunits):
            return round(self.value, precLevel) <= round(other, precLevel)

        # Ensure variables are the same SIID
        pyunits.checkSameSIIDCompare(self, other)

        # If no errors, then conduct comparison
        return round(self.valueBase, precLevel) <= round(other.valueBase, precLevel)

    # --- Comparison magic, greater than or equal
    def __le__(self, other):
        if not isinstance(other, pyunits):
            return round(self.value, precLevel) >= round(other, precLevel)

        # Ensure variables are the same SIID
        pyunits.checkSameSIIDCompare(self, other)

        # If no errors, then conduct comparison
        return round(self.valueBase, precLevel) >= round(other.valueBase, precLevel)

    # --- Comparison magic, equal to
    def __le__(self, other):
        if not isinstance(other, pyunits):
            return round(self.value, precLevel) == round(other, precLevel)

        # Ensure variables are the same SIID
        pyunits.checkSameSIIDCompare(self, other)

        # If no errors, then conduct comparison
        return round(self.valueBase, precLevel) == round(other.valueBase, precLevel)

    # --- Comparison magic, not equal to
    def __le__(self, other):
        if not isinstance(other, pyunits):
            return round(self.value, precLevel) != round(other, precLevel)

        # Ensure variables are the same SIID
        pyunits.checkSameSIIDCompare(self, other)

        # If no errors, then conduct comparison
        return round(self.valueBase, precLevel) != round(other.valueBase, precLevel)

    # Float magic, return float number
    def __float__(self):
        return float(self.valueBase)

    # Int magic, return integer number
    def __int__(self):
        return int(self.valueBase)  # Very dangerous

    # Update function, to change any of the physical variable details
    def update(self, name=None, value=None, unit=None, info=None, formula=None):
        # Update name if available
        if name != None:
            self.name = name

        # Update value if available
        if value != None:
            self.value = value

        # Change info if available
        if info != None:
            self.info = info

        # Change formula if available
        if formula != None:
            self.formula = formula

    # Unit converter function, which returns value of transformed unit
    def convert(self, toUnit, out="variable"):
        # Check that toUnit exists within the unitSet
        try:
            toUnitIndex = unitDict[self.unitSet][0].index(toUnit)
        except ValueError:
            raise Exception("unit to convert to does not exist within the unitSet.")

        # Check also that fromUnit is still within the unitSet
        try:
            fromUnitIndex = unitDict[self.unitSet][0].index(self.unit)
        except ValueError:
            raise Exception("unit to convert from does not exist within the unitSet.")

        # Evaluate the conversion factor
        conversionFactor = (
            unitDict[self.unitSet][1][toUnitIndex]
            / unitDict[self.unitSet][1][fromUnitIndex]
        )

        # Determine desired output type (value or variable.)
        if out == "value":
            return self.value * conversionFactor
        if out == "variable":
            self.value *= conversionFactor
            self.unit = toUnit
            return self
        else:
            raise Exception("unknown output specified in convert() method")

    # Print function, to receive full variable details
    def stringVar(self):
        return "{} = {}{}, unitSet: {}, valueBase: {}, unitBase: {}, info: {}, formula: {}, SIID: {}".format(
            self.name,
            self.value,
            self.unit,
            self.unitSet,
            self.valueBase,
            self.unitBase,
            self.info,
            self.formula,
            self.SIID,
        )

    # UnitSetList generator function
    def findUnitSet(unit):  # unit can be string name or SIID list
        # Evaluate the unitSet. All unit names and SIIDs in unitDict are unique, hence can retrieve either 1 or 0 values
        if isinstance(unit, str):
            return [
                unitSet
                for unitSet, unitLists in unitDict.items()
                if unit in unitLists[0]
            ]  # unitLists[0] contains the units as a list of strings
        elif isinstance(unit, list):
            return [
                unitSet
                for unitSet, unitLists in unitDict.items()
                if unit == unitLists[3]
            ]  # unitLists[3] contains the SSID as a list
        else:
            raise Exception(
                "findUnitSet retrieved input which was neither a string (unit name) nor a list (SIID list)."
            )

    # Establish the unit based on the SIID for non-unitSet numbers.
    def findUnitFromSIID(SIID):
        tmpUnit = ""  # string for the actual units
        lstSIUnits = [
            "m",
            "kg",
            "s",
            "K",
            "A",
            "mole",
            "cd",
        ]  # list of SI units, in the order of the SIID list

        # Generate the unit format
        for unit, power in zip(lstSIUnits, SIID):
            if power != 0:  # If not dimensionless
                if power == 1:  # Simply add the unit (without power)
                    tmpUnit += ("{} ").format(unit)
                else:  # Add the unit with the power
                    tmpUnit += ("{}{} ").format(unit, power)
            else:
                continue  # When unit is dimensionless
        tmpUnit = tmpUnit[:-1]  # Removes last " " space

        return tmpUnit

    def checkSameSIIDCompare(firstVar, secondVar):
        if firstVar.SIID != secondVar.SIID:
            raise Exception(
                "cannot compare values from different unitSets. Unit sets in question: {} and {} | SIID: {} and {}.".format(
                    firstVar.unitSet, secondVar.unitSet, firstVar.SIID, secondVar.SIID
                )
            )


def unitDicTest():
    # Test that each unitSet contains unique units, and that units are not repeated accross unitSets
    lstUnits = []
    for key in unitDict.keys():
        lstUnits.extend(unitDict[key][0])

    if len(set(lstUnits)) != len(lstUnits):
        raise Exception(
            "duplicate units exist either within a unitSet or accross unitsets."
        )


# To run code as script
def main():
    a = pyunits("a", 200, "mm")
    b = pyunits("b", 10 * 1e-3, "cm")
    fy = pyunits("fy=200MPa")

    print(a)
    print(a.stringVar())
    print(b)
    print(fy)
    print(a + b)
    Az_Rd = (a * b) * fy / (3**0.5)
    print(Az_Rd)
    print(Az_Rd.stringVar())

    # test=Av+Av2
    # print('{} = {}{}, unitSet: {}, valueBase: {}, unitBase: {}'.format(test.name, test.value, test.unit, test.unitSet, test.valueBase, test.unitBase))

    # test=Av
    # print('{} = {}{}, unitSet: {}, valueBase: {}, unitBase: {}'.format(test.name, test.value, test.unit, test.unitSet, test.valueBase, test.unitBase))


if __name__ == "__main__":
    unitDicTest()
    main()
