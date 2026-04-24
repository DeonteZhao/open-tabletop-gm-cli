#!/usr/bin/env python3
"""
dice.py — D&D 5e & CoC 7e dice roller

Usage:
    python3 dice.py <notation> [--silent]

Notation supported:
    d20               single d20
    2d6               2 six-sided dice, sum
    d20+5             roll + flat modifier
    4d6kh3            roll 4d6, keep highest 3 (ability score generation)
    4d6kl3            roll 4d6, keep lowest 3
    d20 adv           advantage: roll twice, take higher
    d20 dis           disadvantage: roll twice, take lower
    d20+3 adv         advantage with modifier
    2d6+3             multiple dice + modifier
    d100 b1           CoC 7e: 1 Bonus Die
    d100 p2           CoC 7e: 2 Penalty Dice

Output (unless --silent):
    Rolls: [x, x, x]  →  Total: N
    For advantage/disadvantage, shows both rolls and which was taken.
    Flags natural 20 (CRITICAL HIT) and natural 1 (FUMBLE) on single d20s.
    Flags natural 1 (CRITICAL SUCCESS) and natural 100 (FUMBLE) on single d100s.
"""

import random
import re
import sys


def parse_notation(notation: str):
    """Parse dice notation string. Returns (num_dice, die_size, modifier, keep_mode, keep_count, adv, dis, bonus_dice, penalty_dice)."""
    notation = notation.strip().lower()

    # Strip advantage/disadvantage suffix
    adv = "adv" in notation or "advantage" in notation
    dis = "dis" in notation or "disadvantage" in notation
    notation = re.sub(r'\s*(adv|dis|advantage|disadvantage)\w*', '', notation).strip()
    
    # Strip CoC bonus/penalty dice suffix (e.g., b1, p2)
    bonus_dice = 0
    penalty_dice = 0
    bp_match = re.search(r'\s*(b|p)(\d+)', notation)
    if bp_match:
        if bp_match.group(1) == 'b':
            bonus_dice = int(bp_match.group(2))
        else:
            penalty_dice = int(bp_match.group(2))
        notation = re.sub(r'\s*(b|p)\d+', '', notation).strip()

    # Match: [N]d[S][kh/kl N][+/-M]
    pattern = r'^(\d*)d(\d+)(?:(kh|kl)(\d+))?([+-]\d+)?$'
    m = re.match(pattern, notation.replace(' ', ''))
    if not m:
        raise ValueError(f"Cannot parse dice notation: '{notation}'")

    num_dice = int(m.group(1)) if m.group(1) else 1
    die_size = int(m.group(2))
    keep_mode = m.group(3)       # 'kh' or 'kl' or None
    keep_count = int(m.group(4)) if m.group(4) else None
    modifier = int(m.group(5)) if m.group(5) else 0

    return num_dice, die_size, modifier, keep_mode, keep_count, adv, dis, bonus_dice, penalty_dice


def roll_dice(num_dice, die_size):
    return [random.randint(1, die_size) for _ in range(num_dice)]


def format_modifier(mod):
    if mod == 0:
        return ""
    return f" + {mod}" if mod > 0 else f" - {abs(mod)}"


def run(notation: str, silent: bool = False) -> int:
    num_dice, die_size, modifier, keep_mode, keep_count, adv, dis, bonus_dice, penalty_dice = parse_notation(notation)

    # CoC 7e Bonus / Penalty dice (only meaningful for d100)
    if (bonus_dice > 0 or penalty_dice > 0) and die_size == 100 and num_dice == 1:
        # Roll units digit (1-10, where 10 is 0)
        units = random.randint(1, 10)
        units_val = 0 if units == 10 else units
        
        # Roll tens digit(s) (00, 10, ..., 90)
        num_tens_dice = 1 + bonus_dice + penalty_dice
        tens_rolls = [(random.randint(1, 10) % 10) * 10 for _ in range(num_tens_dice)]
        
        # Combine units and tens (00 + 0 = 100)
        combined_rolls = [tens + units_val if tens + units_val > 0 else 100 for tens in tens_rolls]
        
        if bonus_dice > 0:
            chosen = min(combined_rolls)
            label = f"Bonus Dice ({bonus_dice})"
        else:
            chosen = max(combined_rolls)
            label = f"Penalty Dice ({penalty_dice})"
            
        if not silent:
            print(f"[{label}] Units roll: {units_val}")
            print(f"[{label}] Tens rolls: {tens_rolls}")
            print(f"[{label}] Possible results: {combined_rolls}")
            print(f"Takes roll → Total: {chosen}")
        return chosen

    # Advantage / disadvantage (only meaningful for single d20)
    if adv or dis:
        roll_a = roll_dice(num_dice, die_size)
        roll_b = roll_dice(num_dice, die_size)
        total_a = sum(roll_a) + modifier
        total_b = sum(roll_b) + modifier
        chosen = max(total_a, total_b) if adv else min(total_a, total_b)
        label = "ADV" if adv else "DIS"
        if not silent:
            print(f"[{label}] Roll A: {roll_a} = {total_a}{format_modifier(modifier)}")
            print(f"[{label}] Roll B: {roll_b} = {total_b}{format_modifier(modifier)}")
            taken = "A" if (adv and total_a >= total_b) or (dis and total_a <= total_b) else "B"
            print(f"Takes roll {taken} → Total: {chosen}")
        return chosen

    rolls = roll_dice(num_dice, die_size)

    # Keep highest / lowest
    if keep_mode and keep_count:
        sorted_rolls = sorted(rolls, reverse=(keep_mode == 'kh'))
        kept = sorted_rolls[:keep_count]
        dropped = sorted_rolls[keep_count:]
        result = sum(kept) + modifier
        if not silent:
            kept_str = " + ".join(str(r) for r in kept)
            drop_str = f"  (dropped: {dropped})" if dropped else ""
            mod_str = format_modifier(modifier)
            print(f"Rolls: {rolls}{drop_str}")
            print(f"Kept ({keep_mode}{keep_count}): [{kept_str}]{mod_str} = {result}")
        return result

    result = sum(rolls) + modifier
    if not silent:
        if num_dice == 1 and die_size == 20:
            raw = rolls[0]
            flag = ""
            if raw == 20:
                flag = "  *** CRITICAL HIT (nat 20)! ***"
            elif raw == 1:
                flag = "  *** FUMBLE (nat 1)! ***"
            mod_str = format_modifier(modifier)
            print(f"Roll: {raw}{mod_str} = {result}{flag}")
        elif num_dice == 1 and die_size == 100:
            raw = rolls[0]
            flag = ""
            if raw == 1:
                flag = "  *** CRITICAL SUCCESS (nat 1)! ***"
            elif raw == 100:
                flag = "  *** FUMBLE (nat 100)! ***"
            mod_str = format_modifier(modifier)
            print(f"Roll: {raw}{mod_str} = {result}{flag}")
        else:
            mod_str = format_modifier(modifier)
            print(f"Rolls: {rolls}{mod_str} = {result}")
    return result


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--silent"]
    silent = "--silent" in sys.argv[1:]

    if not args:
        print("Usage: python3 dice.py <notation>  e.g. d20+5  2d6  4d6kh3  d20 adv")
        sys.exit(1)

    notation = " ".join(args)
    result = run(notation, silent=silent)
    if silent:
        print(result)
