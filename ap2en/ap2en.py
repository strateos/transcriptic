from autoprotocol.util import quad_ind_to_num



PLURAL_UNITS = ["microliter", "nanoliter", "milliliter", "second", "minute",
                "hour", "g", "nanometer"]

TEMP_DICT = {"cold_20": "-20 degrees celsius", "cold_80": "-80 degrees celsius",
             "warm_37": "37 degrees celsius", "cold_4": "4 degrees celsius",
             "warm_30": "30 degrees celsius"}


def parse(protocol_obj):
    instructions = protocol_obj['instructions']
    parsed_output = []
    for i in instructions:
        output = eval(i['op'])(i)
        try:
            parsed_output.extend(output) if isinstance(output, list) else parsed_output.append(output)
        except NameError:
            parsed_output.append("[Unknown instruction]")

    for i, p in enumerate(parsed_output):
        print "%d. %s" % (i+1, p)

def absorbance(opts):
    well_list = "wells " + (', ').join(str(x) for x in opts['wells'])
    if len(opts['wells']) > 10:
        well_list = str(len(well_list)) + " wells"
    return "Measure absorbance at %s for %s of plate %s" % (unit(opts['wavelength']),
                                                    well_list, opts['object'])

def autopick(opts):
    pass

def consolidate(opts):
    pass

def cover(opts):
    return "Cover %s with a %s lid" % (opts['object'], opts['lid'])

def dispense(opts):
    pass

def flash_freeze(opts):
    return "Flash freeze %s for %s" % (opts['object'], unit(opts['duration']))

def fluorescence(opts):
    well_list = "wells " + (', ').join(str(x) for x in opts['wells'])
    if len(opts['wells']) > 10:
        well_list = str(len(well_list)) + " wells"
    return ("Read fluorescence of %s of plate %s at excitation wavelength %s"
            " and emission wavelength %s" % (well_list, opts['object'],
                                             unit(opts['excitation']),
                                             unit(opts['emission'])))

def gel_separate(opts):
    return ("Perform gel electrophoresis using "
            "a %s agarose gel for %s" % (opts['matrix'].split(',')[1][:-1],
                                         unit(opts['duration'])))

def incubate(opts):
    return "Incubate %s at %s for %s" % (opts['object'],
                                         TEMP_DICT[opts['where']],
                                         unit(opts['duration']))

def image_plate(opts):
    return "Take an image of %s" % opts['object']

def luminescence(opts):
    well_list = "wells " + (', ').join(str(x) for x in opts['wells'])
    if len(opts['wells']) > 10:
        well_list = str(len(well_list)) + " wells"
    return "Read luminescence of %s of plate %s" % (well_list, opts['object'])

def mix(opts):
    return ("Mix well %s of plate %s %d times with "
           "a volume of %s" % (well(opts['well']),
                               platename(opts['well']),
                               opts['repetitions'], unit(opts['volume'])))

def oligosynthesize(opts):
    pass

def provision(opts):
    for t in opts['to']:
        return "Provision %s of resource with ID %s to well %s of plate %s" % \
            (unit(t['volume']), opts['resource_id'], well(t['well']), platename(t['well']))

def sangerseq(opts):
    pass

def seal(opts):
    return "Seal %s (%s)" % (opts['object'], opts['type'])

def spin(opts):
    return "Spin %s for %s at %s" % (opts['object'], unit(opts['duration']),
                                     unit(opts['acceleration']))
def spread(opts):
    return ["Spread %s of bacteria from well %s of %s "
           "to well %s of agar plate %s" % (opts['volume'], well(opts['from']),
            platename(opts['to']), well(opts['from']), platename(opts['from']))]

def stamp(opts):
    stamps = []
    for t in opts['transfers']:
        stamps.append("Transfer from %s quadrant %s to %s quadrant %s" %
                      (platename(t['from']), well(t['from']),
                       platename(t['to']), well(t['to']))
                      )
    return stamps

def pipette(opts):
    pipettes = []
    for g in opts['groups']:
        for pip in g:
            if pip == "mix":
                for m in g[pip]:
                    pipettes.append(mix(m))
            elif pip == "transfer":
                pass
            elif pip == "distribute":
                pass

    return pipettes



def uncover(opts):
    return "Uncover %s" % opts['object']

def unseal(opts):
    return "Unseal %s" % opts['object']

def platename(ref):
    return ref.split('/')[0]

def well(ref):
    return ref.split('/')[1]

def unit(u):
    value = u.split(':')[0]
    unit = u.split(':')[1]
    return "%s %s" % (value, (unit + "s" if (float(value) > 1 and
                                             unit in PLURAL_UNITS) else unit))

