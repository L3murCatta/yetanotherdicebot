from datetime import date
from secrets import choice
from requests import post
from telegram.ext import Updater, CommandHandler

numtimes = 1
fate = 0
keynum = 0
currentdate = date.today()
modes = {}
sorts = {}
counts = {}
helptext = """========== MODES ==========

"/mode good" changes the current mode to good. In this mode, the rolls are slightly higher on average.
"/mode normal" resets the current mode to normal (set by default).
"/mode bad" changes the current mode to bad. In this mode, the rolls are slightly lower on average.

"/sort" enables "sort" mode.
"/sort d" enables descending sort.
"/sort off" disables sort (set by default).

"/count" enables "count" mode, displaying every unique value and quantity of its instances in the roll.
"/count raw" ignores "a" and "c" modifiers when counting (refer to Dice Roll section for details).
"/count off" disables count (set by default).

========== DICE ROLL ==========

"/d R" and "/dice R" are equivalent commands.
Examples:
"/d d20"
"/d d6 + 2d20+3"
"/d 12d10r<2" rerolls all dice with values greater than 7. ">", ">=", "<" and "<=" are available comparison signs. If no sign is provided (as in "d20r1", only specified values are rerolled.
"/d 12d10t>7f1" counts successes and failures (same syntax as above).
"/d 12d10!>8" explodes all dice under specified conditions (same syntax as above). Use "!m" notation to explode highest possible values only.
"/d d10c>=3" restricts possible values as specified (same syntax as above). In the given example, if 1 or 2 is rolled, it would be set to 3.
"/d 20d20a+4" adds the specified modifier to EVERY roll made.
"/d 4d6d1", "/d 4d6k3" drops or keeps specified number of values. "d" or "dl" drops lowest, "dh" drops highest, "kl" keeps lowest, "k" or "kh" keeps highest.

Any aforementioned modifiers can be used in any combinations.
Use "xN" notation right after the command (e. g. "/d x6 4d6d1") to do multiple identical rolls.

========== SHORTCUTS ==========

"/g" rolls 3d6 (GURPS roll).
"/p" rolls d100 (percentile roll).
"/f" rolls 4 Fate dice (FATE roll). "/f X" adds X to the roll.
"/ff" rolls d6-d6 (alternative FATE roll). "/ff X" adds X to the roll.
"/w X Y Z" rolls Xd10t>Yf1!>=Z (old World of Darkness roll). Only X is mandatory; Y is set at 6 by default.
"/n X Y" rolls Xd10t>7!>=Y (new World of Darkness roll). Only X is mandatory; Y is set at 10 by default.

"xN" notation works for all shortcuts as well.

Good luck!"""

def customrandom(amount, low, high):
    global currentdate, keynum
    keys = ["0496cfd9-1838-45ec-a0de-19452f3d60a2",
            "443605e5-1b6f-4918-934e-5d4813b7c9a0",
            "9145ee61-696c-4fb4-9c8a-70e92b535265",
            "1868a3f3-dc87-4493-906b-2964c0cfab76",
            "a7dff9fd-94bb-4511-935b-610a584e207f",
            "8697f146-beb8-4c8f-9609-d03f6e7db547",
            "8672f846-3322-4a88-98c0-588743060f9f",
            "549f16f8-9fa7-4408-9ecc-5e7d5f7000ce"]
    request = {
        "jsonrpc": "2.0",
        "method": "generateIntegers",
        "params": {
            "apiKey": keys[keynum],
            "n": amount,
            "min": low,
            "max": high
            },
        "id": 1
    }
    if currentdate != date.today():
        currentdate = date.today()
        keynum = 0
        return customrandom(amount, low, high)
    if keynum < 0:
        return [choice(range(low, high+1)) for _ in range(amount)]
    try:
        resp = post("https://api.random.org/json-rpc/1/invoke",
                    json = request, timeout = 5)
    except Exception:
        keynum += 1
        if keynum >= len(keys):
            keynum = -1
        return customrandom(amount, low, high)
    
    if resp.json().get("error") == None:
        return resp.json().get('result').get('random').get('data')
    else:
        keynum += 1
        if keynum >= len(keys):
            keynum = -1
        return customrandom(amount, low, high)

def rolldie(amount, die, mode):
    res = []
    if mode == 0:
        return customrandom(amount, 1, die)
    r = customrandom(amount*3, 1, die)
    for i in range(amount):
        a = r[i]
        b = r[i+amount]
        c = r[i+2*amount]
        if a > b and mode == 1 or a < b and mode == -1:
            res.append(a)
        else:
            res.append(c)
    return res

def splitbysigns(st):
    global numtimes
    numtimes = 1
    if "x" in st:
        st = st.strip()
        st = st.split(maxsplit=1)
        if st[0][0] != "x":
            raise Exception("Wrong position of rolls number ('x')")
        try:
            numtimes = int(st[0][1:])
        except Exception:
            raise Exception("Bad rolls number: {}".format(st[0]))
        st = st[1]
            
    st = st.replace(" ", "")
    nopluses = st.split("+")
    pluses = []
    added = ""
    for element in nopluses:
        if element[0] != "-":
            added += "+"
        if element[len(element)-1] in ["a", "r", "t", "f", "!", "p", ">", "<", "="]:
            added += element
        else:
            pluses.append(added + element)
            added = ""
    minuses = []
    for substring in pluses:
        nominuses = substring.split("-")
        added = ""
        for element in nominuses:
            if element == "":
                continue
            if element[0] != "+":
                added = added + "-"
            if element[len(element)-1] in ["a", "r", "t", "f", "!", "p", ">", "<", "="]:
                added = added + element
            else:
                minuses.append(added + element)
                added = ""
    return minuses

class diceroll:
    def __init__(self):
        self.die = 20
        self.amount = 1
        self.reroll = []
        self.threshold = []
        self.failure = []
        self.modifier = 0
        self.explode = []
        self.compound = []
        self.penetrate = []
        self.drop = 0
        self.highdrop = 0
        self.lowconstr = -float("Inf")
        self.highconstr = float("Inf")
    def debugprint(self):
        print(', '.join("%s: %s" % item for item in vars(self).items()))

def getnum(st):
    for i in range(1, len(st)+1):
        if not st[:i].isdigit():
            return [st[:i-1], st[i-1:]]
    return [st, ""]

def parsecomp(st):	#get comparison sign
    comp = 0
    if st == "":
        return 0, ""
    if st[0] == ">":
        if st[1] == "=":
            comp = 2
            st = st[2:]
        else:
            comp = 1
            st = st[1:]
    else:
        if st[0] == "<":
            if st[1] == "=":
                comp = 4
                st = st[2:]
            else:
                comp = 3
                st = st[1:]
    if st == "":
        raise Exception("A numerical value is required")
    if not st[0].isdigit() and st[0] not in ["+", "-"]:
        raise Exception("A numerical value is required")
    return comp, st

def parsesign(st):	#get plus or minus
    sign = 1
    if st == "":
        raise Exception("A numerical value is required")
    if st[0] == "+":
        st = st[1:]
    else:
        if st[0] == "-":
            sign = -1
            st = st[1:]
    if st == "":
        raise Exception("A numerical value is required")
    if not st[0].isdigit():
        raise Exception("A numerical value is required")
    return sign, st

def parserange(die, mod, added, comp):
    low = 0
    high = 0
    if comp == 0:
        if mod - added in range(1, die+1):
            low = mod - added
            high = low+1
            return low, high
        else:
            raise Exception("Wrong modifier value: {}".format(mod))
    if comp in [1, 2]:
        high = die+1
        low = mod - added
    if comp in [3, 4]:
        low = 1
        high = mod - added
    if comp == 1:
        low = low+1
    if comp == 4:
        high = high+1
    low = max(low, 1)
    high = min(high, die+1)
    if low >= high:
        raise Exception("Wrong modifier value: {}".format(mod))
    return low, high

def parsemodifiers(d, st):
    comp = 0
    mod = 0
    sign = 1
    a = 0
    ################search for addition#####################
    i = st.find("a")
    if i >= 0:
        cut = st[i+1:]
        mod, cut = parsesign(cut)
        cut = getnum(cut)
        mod = mod * int(cut[0])
        d.modifier = mod
    #######################main block#########################
    while st != "":
        c = st[0]
        st = st[1:]
        
        if c == "!":
            if st[0] == "!":
                c = "!!"
                st = st[1:]
            else:
                if st[0] == "p":
                    c = "!p"
                    st = st[1:]
    
        if c in ["r", "t", "f", "!", "!!", "!p"]:
            if st == "":
                raise Exception("A numerical value is required")
            if c[0] == "!" and st[0] == "m" :
                low = d.die
                high = d.die + 1
                st = st[1:]
            else:
                comp, st = parsecomp(st)
                sign, st = parsesign(st)
                st = getnum(st)
                mod = int(st[0]) * sign
                st = st[1]
                low, high = parserange(d.die, mod, d.modifier, comp)
        if c in ["d", "k"]:
            #print(len(st))
            if len(st) < 1:
                raise Exception("A numerical value is required")
            if st[0] in ["h", "l"] and len(st)<2:
                raise Exception("A numerical value is required")
        
        ##################rerolls#################################
        if c == "r":
            for i in range(low, high):
                if not i in d.reroll:
                    d.reroll.append(i)
            if len(d.reroll) >= d.die:
                raise Exception("Wrong reroll value")
            continue
        ###############threshold###########################
        if c == "t":
            for i in range(low, high):
                if not i in d.threshold:
                    d.threshold.append(i)
            continue
        #################failure###########################
        if c == "f":
            for i in range(low, high):
                if not i in d.failure:
                    d.failure.append(i)
            continue
        ###########explode################################
        if c == "!":
            for i in range(low, high):
                if not i in d.explode:
                    d.explode.append(i)
            if len(d.explode) >= d.die:
                raise Exception("Wrong explode value")
            continue
        ##############compound############################
        if c == "!!":
            for i in range(low, high):
                if not i in d.compound:
                    d.compound.append(i)
            if len(d.compound) >= d.die:
                raise Exception("Wrong compound value")
            continue
        ###################penetrate######################
        if c == "!p":
            for i in range(low, high):
                if not i in d.penetrate:
                    d.penetrate.append(i)
            if len(d.penetrate) >= d.die:
                raise Exception("Wrong penetrate value")
            continue
        ##############added modifier##################
        if c == "a":
            a = a+1
            if a > 1:
                raise Exception("Only one addition is allowed")
            if st[0] in ["+", "-"]:
                st = st[1:]
            st = getnum(st)
            st = st[1]
            continue
        #############drop/keep######################
        if c in ["d", "k"]:
            mod = 0 #lowest
            if st[0] == "l":
                mod = -1
                st = st[1:]
            if st[0] == "h": #highest
                mod = 1
                st = st[1:]
            st = getnum(st)
            if c == "d":
                if mod == 1:
                    d.highdrop = int(st[0])
                else:
                    d.drop = int(st[0])
            else:
                if mod == -1:
                    d.highdrop = d.amount - int(st[0])
                else:
                    d.drop =	d.amount - int(st[0])
            st = st[1]
            continue
        ################constraint####################
        if c == "c":
            comp, st = parsecomp(st)
            if comp == 0:
                raise Exception("A comparison sign is required")
            sign, st = parsesign(st)
            st = getnum(st)
            mod = int(st[0]) * sign
            st = st[1]
            if comp == 1:
                d.lowconstr = mod+1
            if comp == 2:
                d.lowconstr = mod
            if comp == 3:
                d.highconstr = mod-1
            if comp == 4:
                d.highconstr = mod
            if d.highconstr < d.lowconstr:
                raise Exception("Bad constraint")
            continue
        raise Exception("Unknown modifier: {}".format(c))
    return d

def parseroll(st):
    d = diceroll()
    sp = st.split("d", maxsplit=1)
    if sp[0] == "":
        d.amount = 1
    else:
        try:
            d.amount = int(sp[0])
        except Exception:
            raise Exception("Bad dice amount")
    sp = sp[1]
    if sp[0] == "F":
        d.die = -1
        sp = sp[1:]
    else:
        sp = getnum(sp)
        if sp == "":
            raise Exception("Bad die")
        d.die = int(sp[0])
        sp = sp[1]
    if sp == "":
        return d
    d = parsemodifiers(d, sp)
    return d

def numform(i):
    if not fate:
        return i
    if i<2:
        return "-"
    if i == 2:
        return "0"
    if i > 2:
        return "+"

def stringify(d, r, modifier, sort):
    res = ""
    if not r:
        return res
    if sort == 1:
        r.sort()
    if sort == -1:
        r.sort(reverse = True)
    res = "["
    for i in r:
            ci = max(d.lowconstr, min(d.highconstr, i+modifier))
            if not fate and modifier != 0 or fate and modifier != -2 or ci != i+modifier:
                res += "<b>{}</b>({}), ".format(ci, numform(i))
            else:
                res += "{}, ".format(numform(i))
    res = res[:-2] + "]"
    return res

def rerollexplode(d, r, total, res, mode, sort):
    toreroll = 0
    toexplode = 0
    
    co = []
    
    for i in range(0, len(r)):
        if r[i]+d.modifier < d.lowconstr:
            total += d.lowconstr - r[i]-d.modifier
            co.append(r[i])
            r[i] = d.lowconstr - d.modifier
        if r[i]+d.modifier > d.highconstr:
            total -= r[i]+d.modifier - d.highconstr
            co.append(r[i])
            r[i] = d.highconstr - d.modifier

    rr = r[:]
    for i in r:
        if i in d.reroll:
            rr.remove(i)
            total -= i + d.modifier
            toreroll += 1
    r = rr
    while toreroll > 0:
        r1 = rolldie(toreroll, d.die, mode)
        res += "r"+stringify(d, r1, d.modifier, sort)
        total += sum(r1)+len(r1)*d.modifier
        toreroll = 0
        rr = r1[:]
        for i in r1:
            if i in d.reroll:
                rr.remove(i)
                total -= i + d.modifier
                toreroll += 1
        r += rr

    toexplode += sum(i in d.explode for i in r)
    if toexplode > 0:
        r1 = rolldie(toexplode, d.die, mode)
        res += "!"+stringify(d, r1, d.modifier, sort)
        total += sum(r1)+len(r1)*d.modifier
        r2, total, res, co2 = rerollexplode(d, r1, total, res, mode, sort)
        r += r2
        co += co2
    
    return r, total, res, co
    
def roll(d, sign, mode, sort, count, fl):
    global fate
    fate = 0
    if d.die == -1:
        fate = 1
        d.die = 3
        d.modifier -= 2
    
    r = rolldie(d.amount, d.die, mode)
    res = stringify(d, r, d.modifier, sort)
    total = sum(r)+len(r)*d.modifier
    r, total, res, co = rerollexplode(d, r, total, res, mode, sort)
    
    if d.drop + d.highdrop > len(r):
        raise Exception("More dice dropped than rolled")
    if d.drop + d.highdrop > 0:
        sortr = r[:]
        sortr.sort()
        r = sortr[d.drop : len(sortr) - d.highdrop]
        total -= (d.drop + d.highdrop)*d.modifier
        for i in sortr[:d.drop]:
            total -= i
        for i in sortr[len(sortr)-d.highdrop:]:
            total -= i
    
    total *= sign
    res+= " = {}\n".format(("{}" if fl else "<b>{}</b>").format(total))

    if count > 0:
    
        if count == 2 and d.drop+d.highdrop < len(co):
            co.sort()
            for i in range(0, d.drop):
                if co[i]+d.modifier < d.lowconstr:
                    co = co[1:]
                    r.remove(d.lowconstr)
                else:
                    break
            co.sort(reverse = True)
            for i in range(0, d.highdrop):
                if co[i]+d.modifier > d.highconstr:
                    co = co[1:]
                    r.remove(d.highconstr)
                else:
                    break
            r += co
        
        uniques = sorted(list(set(r)), reverse = (sort == -1))
        for u in uniques:
            c = r.count(u)
            if fate and (d.modifier == -2 or count == 2):
                v = numform(u)
            else:
                if count == 2:
                    v = u
                else:
                    v = u + d.modifier
            res += "[<b>{}</b>: x{}], ".format(v, c)
        res = res[:-2] + "\n"

    if d.drop + d.highdrop > 0:
        res += "Dropped: {}\n".format(sortr[:d.drop]+sortr[len(sortr)-d.highdrop:])
    
    if d.threshold:
        successes = sum(i in d.threshold for i in r)
        res += "Successes: <b>{}</b>\n".format(successes)
    if d.failure:
        failures = sum(i in d.failure for i in r)
        res += "Failures: <b>{}</b>\n".format(failures)
    if d.threshold and d.failure:
        res += "Total successes: <b>{}</b>\n".format(successes-failures)
    return total, res


def parseandroll(st, mode, sort, count):
    parts = splitbysigns(st)
    res = ""

    for _ in range(0, numtimes):
        total = 0
        totalst = ""
        try:
            for p in parts:
                if "d" in p:
                    if p[0] == "-":
                        sign = -1
                    else:
                        sign = 1
                    p = p[1:]
                    d = parseroll(p)
                    if sign == -1:
                        res += "-"
                    res += p+": "
                    t, s = roll(d, sign, mode, sort, count, len(parts) > 1)
                    res += s
                    total += t
                    if t >= 0:
                        totalst += "+"
                    totalst += str(t)
                else:
                    try:
                        total += int(p)
                    except Exception:
                        raise Exception("Bad number: {}".format(p))
                    totalst += p
                
        except Exception as e:
            res = str(e)
            return res
        
        if totalst[0] == "+":
            totalst = totalst[1:]
        if len(parts) > 1:
            res += "Total: {} = <b>{}</b>\n".format(totalst, total)
        if _ < numtimes-1:
            res += "\n"
    res = res[:-1]
    return res

def sortf(bot, update):
    global sorts
    if update.message.text.strip().find(' ') == -1:
        sorts[update.message.chat.id] = 1
        update.message.reply_text("Sorting enabled")
        return
    t = update.message.text[update.message.text.find(' ')+1:]
    if t == "d":
        sorts[update.message.chat.id] = -1
        update.message.reply_text("Descending sorting enabled")
        return
    if t == "off":
        sorts[update.message.chat.id] = 0
        update.message.reply_text("Sorting disabled")
        return
    sorts[update.message.chat.id] = 1
    update.message.reply_text("Sorting enabled")

def countf(bot, update):
    global counts
    if update.message.text.strip().find(' ') == -1:
        counts[update.message.chat.id] = 1
        update.message.reply_text("Counting enabled")
        return
    t = update.message.text[update.message.text.find(' ')+1:]
    if t == "raw":
        counts[update.message.chat.id] = 2
        update.message.reply_text("Couting raw enabled")
        return
    if t == "off":
        counts[update.message.chat.id] = 0
        update.message.reply_text("Counting disabled")
        return
    counts[update.message.chat.id] = 1
    update.message.reply_text("Counting enabled")

#def good(bot, update):
#    global modes
#    modes[update.message.chat.id] = 1
#    update.message.reply_text("Commencing good mode")

#def normal(bot, update):
#    global modes
#    modes[update.message.chat.id] = 0
#    update.message.reply_text("Commencing normal mode")

#def bad(bot, update):
#    global modes
#    modes[update.message.chat.id] = -1
#    update.message.reply_text("Commencing bad mode")

def modef(bot, update):
    global modes
    if update.message.text.strip().find(' ') == -1:
        update.message.reply_text("No mode specified")
        return
    t = update.message.text[update.message.text.find(' ')+1:]
    if t == "good":
        modes[update.message.chat.id] = 1
        update.message.reply_text("Commencing good mode")
        return
    if t == "normal":
        modes[update.message.chat.id] = 0
        update.message.reply_text("Commencing normal mode")
        return
    if t == "bad":
        modes[update.message.chat.id] = -1
        update.message.reply_text("Commencing bad mode")
        return
    update.message.reply_text("Mode not recognized")
    return

def dice(bot, update):
    try:
        mode = modes[update.message.chat.id]
    except Exception:
        modes[update.message.chat.id] = 0
        mode = 0
    finally:        
        try:
            sort = sorts[update.message.chat.id]
        except Exception:
            sorts[update.message.chat.id] = 0
            sort = 0
        finally:
            try:
                count = counts[update.message.chat.id]
            except Exception:
                counts[update.message.chat.id] = 0
                count = 0
            finally:
                update.message.reply_text(("" if mode == 0 else "{} mode:\n".format("Bad" if mode == -1 else "Good")) + parseandroll(update.message.text[update.message.text.find(' ')+1:], mode, sort, count), parse_mode = "HTML")

def d(bot, update):
    dice(bot, update)

def parsex(t):
    x = 1
    res = ""
    if t.strip().find(" ") == -1 or t.find('x') == -1 or len(t.strip().split()) < 2:
        return 1, t
    s = t.strip().split(maxsplit = 2)
    sx = s[1]
    if sx == "":
        return 1, t
    if sx[0] != 'x':
        return 1, t
    try:
        x = int(sx[1:])
    except Exception:
        return 1, t
            
    if len(s)>2:
    	res = s[0] + " " + s[2]
    else:
    	res = s[0]
    return x, res

def f(bot, update):
    t = update.message.text
    n, t = parsex(t)
    res = "/dice x{} 4dF".format(n)
    x = 0
    if t.strip().find(" ") != -1:
        try:
            x = int(t[t.find(" ")+1:])
        except Exception:
            update.message.reply_text("Bad syntax")
            return
    if x > 0:
        res += "+"
    if x != 0:
        res += str(x)
    update.message.text = res
    dice(bot, update)

def ff(bot, update):
    t = update.message.text
    n, t = parsex(t)
    res = "/dice x{} d6-d6".format(n)
    x = 0
    if t.strip().find(" ") != -1:
        try:
            x = int(t[t.find(" ")+1:])
        except Exception:
            update.message.reply_text("Bad syntax")
            return
    if x > 0:
        res += "+"
    if x != 0:
        res += str(x)
    update.message.text = res
    dice(bot, update)   
	
def g(bot, update):
    n, _ = parsex(update.message.text)
    update.message.text = "/dice x{} 3d6".format(n)
    dice(bot, update)

def p(bot, update):
    n, _ = parsex(update.message.text)
    update.message.text = "/dice x{} d100".format(n)
    dice(bot, update)
	
def n(bot, update):
    x = 0
    y = 10
    t = update.message.text
    n, t = parsex(t)
    t = t.split()
    try:
        x = int(t[1])
        if len(t) > 2:
            y = int(t[2])
    except Exception:
        update.message.reply_text("Bad syntax")
        return
    update.message.text = "/dice x{} {}d10t>=8!>={}".format(n, x, y)
    dice(bot, update)
	
def w(bot, update):
    x = 0
    y = 6
    z = 0
    t = update.message.text
    n, t = parsex(t)
    t = t.split()
    try:
        x = int(t[1])
        if len(t) > 2:
            y = int(t[2])
        if len(t) > 3:
            z = int(t[3])
    except Exception:
        update.message.reply_text("Bad syntax")
        return
    res = "/dice x{} {}d10t>={}f1".format(n, x, y)
    if z > 0:
        res += "!>={}".format(z)
    update.message.text = res
    dice(bot, update)

def helpf(bot, update):
    update.message.reply_text(helptext)

updater = Updater('379931845:AAE063r0aMOGrHgyHP_F9-9Sll4ckeNTD1U')

updater.dispatcher.add_handler(CommandHandler('dice', dice))
updater.dispatcher.add_handler(CommandHandler('d', d))
#updater.dispatcher.add_handler(CommandHandler('good', good))
#updater.dispatcher.add_handler(CommandHandler('normal', normal))
#updater.dispatcher.add_handler(CommandHandler('bad', bad))
updater.dispatcher.add_handler(CommandHandler('mode', modef))
updater.dispatcher.add_handler(CommandHandler('sort', sortf))
updater.dispatcher.add_handler(CommandHandler('count', countf))
updater.dispatcher.add_handler(CommandHandler('f', f))
updater.dispatcher.add_handler(CommandHandler('ff', ff))
updater.dispatcher.add_handler(CommandHandler('p', p))
updater.dispatcher.add_handler(CommandHandler('g', g))
updater.dispatcher.add_handler(CommandHandler('n', n))
updater.dispatcher.add_handler(CommandHandler('w', w))
updater.dispatcher.add_handler(CommandHandler('help', helpf))

updater.start_polling()
updater.idle()
