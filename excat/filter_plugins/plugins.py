# Copyright (C) 2023 Intel Corporation
# SPDX-License-Identifier: Apache-2.0

"""Custom filter plugins module"""

def dec2bin(dec):
    """Convert decimal to binary (output as string)."""
    return format(dec, 'b')

def dec2hex(dec):
    """Convert decimal to hex (output as string)."""
    return format(dec, 'x')

def hex2bin(hex_nr):
    """Convert hex (string) to binary (output as string)."""
    return format(int('0x'+ hex_nr,base=16), 'b')

def is_consecutive(bitmask_dec):
    """Check if bits are consecutive."""
    one, onezero, onezeroone = False, False, False
    len_bitmask = len(dec2bin(bitmask_dec))
    for i in range(len_bitmask):
        position = 1 << (len_bitmask - (i+1))
        if bitmask_dec&position and not one:
            one = True
        elif not(bitmask_dec&position) and one and not onezero:
            onezero = True
        elif bitmask_dec&position and onezero:
            onezeroone = True
    return not onezeroone

def cacheways2bitmask(cacheways):
    """Convert cacheways to binary mask (output as string)."""
    bitmask_bin = 0b0
    for i in range(cacheways):
        bitmask_bin = bitmask_bin | 0b1 << i
    return format(bitmask_bin, 'b')

def bitmask2cacheways(bitmask_bin_str):
    """Count number of cacheways in bitmask (input as string)."""
    bitmask_bin=int(bitmask_bin_str,base=2)
    cacheways=0
    for i in range(len(bitmask_bin_str)):
        if (0b1<<i)&bitmask_bin:
            cacheways+=1
    return cacheways

def getlowestone(bitmask_bin_str):
    """Get lowest 1 in binary mask (input as string)."""
    bitmask_bin=int(bitmask_bin_str,base=2)
    len_bitmask = len(bitmask_bin_str)
    for i in range(len_bitmask):
        position = 0b1 << (len_bitmask - (i+1))
        if position&bitmask_bin:
            lowest_one_index = len_bitmask - (i+1)
    return lowest_one_index

def binshiftleft(bitmask_bin_str, shiftby):
    """Shift bitmask_bin (string) by shiftby to the left."""
    return format(int(bitmask_bin_str,base=2) << shiftby, 'b')

def dec_or(in1, in2):
    """Bitwise or of two decimal numbers (output decimal)."""
    return in1 | in2

def dec_and(in1, in2):
    """Bitwise and of two decimal numbers (output decimal)."""
    return in1 & in2

def get_unused(bitmask_dec):
    """Get unused slots."""
    in_slot = False
    index, length = 0,0
    slots = []
    len_bitmask = len(dec2bin(bitmask_dec))
    for i in range(len_bitmask):
        if not(bitmask_dec & (1<<i)): # pylint: disable=superfluous-parens
            if not in_slot:
                index, length = i, 1
                in_slot = True
            else:
                length += 1
        else:
            if in_slot:
                slot_bitmask = format(int(cacheways2bitmask(length),base=2) << index, 'x')
                slots.append([index, length, slot_bitmask])
                in_slot = False
    return slots

class FilterModule(): # pylint: disable=too-few-public-methods
    """Provide custom filters."""
    def filters(self):
        """Return filters."""
        return {
            'dec2bin': dec2bin,
            'dec2hex': dec2hex,
            'hex2bin': hex2bin,
            'is_consecutive': is_consecutive,
            'cacheways2bitmask': cacheways2bitmask,
            'bitmask2cacheways': bitmask2cacheways,
            'getlowestone': getlowestone,
            'binshiftleft': binshiftleft,
            'dec_or': dec_or,
            'dec_and': dec_and,
            'get_unused': get_unused
        }
