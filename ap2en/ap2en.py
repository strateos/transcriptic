from autoprotocol.util import quad_ind_to_num



PLURAL_UNITS = ["microliter", "nanoliter", "milliliter", "second", "minute",
                "hour", "g", "nanometer"]

def parse(protocol_obj):
    instructions = protocol_obj['instructions']
    parsed_output = []
    for i in instructions:
        try:
            parsed_output.append(eval(i['op'])(i))
        except NameError:
            parsed_output.append("[unknown instruction]")

    for i, p in enumerate(parsed_output):
        print "%d. %s" % (i+1, p)


def cover(opts):
    return "Cover %s with a %s lid" % (opts['object'], opts['lid'])

def provision(opts):
    for t in opts['to']:
        return "Provision %s of resource with ID %s to well %s of plate %s" % \
            (unit(t['volume']), opts['resource_id'], well(t['well']), platename(t['well']))

def seal(opts):
    return "Seal %s (%s)" % (opts['object'], opts['type'])

def spin(opts):
    return "Spin %s for %s at %s" % (opts['object'], unit(opts['duration']),
                                     unit(opts['acceleration']))

def stamp(opts):
    stamps = []
    for t in opts['transfers']:
        stamps.append("Transfer from %s quadrant %s to %s quadrant %s" %
                      (platename(t['from']), well(t['from']),
                       platename(t['to']), well(t['to']))
                      )
    for s in stamps:
        return s


def pipette(opts):
    pass

def uncover(opts):
    return "Uncover %s" % opts['object']
def platename(ref):
    return ref.split('/')[0]

def well(ref):
    return ref.split('/')[1]

def unit(u):
    value = u.split(':')[0]
    unit = u.split(':')[1]
    return "%s %s" % (value, (unit + "s" if (float(value) > 1 and
                                             unit in PLURAL_UNITS) else unit))

