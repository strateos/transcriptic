import autoprotocol.util


PLURAL_UNITS = ["microliter", "nanoliter", "milliliter", "second", "minute",
                "hour", "g", "nanometer"]

TEMP_DICT = {"cold_20": "-20 degrees celsius", "cold_80": "-80 degrees celsius",
             "warm_37": "37 degrees celsius", "cold_4": "4 degrees celsius",
             "warm_30": "30 degrees celsius", "ambient": "room temperature"}


class AutoprotocolParser(object):
    def __init__(self, protocol_obj, parsed_output = None):
        self.parse(protocol_obj)

    def parse(self, obj):
        self.instructions = obj['instructions']
        parsed_output = []
        for i in self.instructions:
            try:
                output = getattr(self, i['op'])(i)
                parsed_output.extend(output) if isinstance(output, list) else parsed_output.append(output)
            except AttributeError:
                parsed_output.append("[Unknown instruction]")
        for i, p in enumerate(parsed_output):
            print "%d. %s" % (i+1, p)


    def absorbance(self, opts):
        return "Measure absorbance at %s for %s of plate %s" % (self.unit(opts['wavelength']),
                                                        self.well_list(opts['wells']), opts['object'])

    def autopick(self, opts):
        return "Pick %d colonies from well %s of plate %s into %s" % (len(opts['to']),
                                                              self.well(opts['from']),
                                                              self.platename(opts['from']),
                                                              self.well_list(opts['to']))

    def cover(self, opts):
        return "Cover %s with a %s lid" % (opts['object'], opts['lid'])

    def dispense(self, opts):
        return "Dispense %s to %d column(s) of %s" % (opts['reagent'],
                                                    len(opts['columns']),
                                                    opts['object'])

    def flash_freeze(self, opts):
        return "Flash freeze %s for %s" % (opts['object'], self.unit(opts['duration']))

    def fluorescence(self, opts):
        return ("Read fluorescence of %s of plate %s at excitation wavelength %s"
                " and emission wavelength %s" % (self.well_list(opts['wells']),
                                                 opts['object'],
                                                 self.unit(opts['excitation']),
                                                 self.unit(opts['emission'])))

    def gel_separate(self, opts):
        return ("Perform gel electrophoresis using "
                "a %s agarose gel for %s" % (opts['matrix'].split(',')[1][:-1],
                                             self.unit(opts['duration'])))

    def incubate(self, opts):
        shaking = " (shaking)" if opts['shaking'] else ""
        return "Incubate %s at %s for %s%s" % (opts['object'],
                                             TEMP_DICT[opts['where']],
                                             self.unit(opts['duration']),
                                             shaking)

    def image_plate(self, opts):
        return "Take an image of %s" % opts['object']

    def luminescence(self, opts):
        return "Read luminescence of %s of plate %s" % (self.well_list(opts['wells']), opts['object'])

    def oligosynthesize(self, opts):
        return ["Oligosynthesize sequence '%s' into '%s'" % (o['sequence'], o['destination']) for o in opts['oligos']]

    def provision(self, opts):
        provisions = []
        for t in opts['to']:
            provisions.append("Provision %s of resource with ID %s to well %s of container %s" % \
                (self.unit(t['volume']), opts['resource_id'], self.well(t['well']), self.platename(t['well'])))
        return provisions

    def sanger_sequence(self, opts):
        seq = "Sanger sequence %s of plate %s" % (self.well_list(opts['wells']), opts['object'])
        if opts['type'] == "standard":
            return seq
        elif opts['type'] == "rca":
            return seq + " with %s" % self.platename(opts['primer'])


    def seal(self, opts):
        return "Seal %s (%s)" % (opts['object'], opts['type'])

    def spin(self, opts):
        return "Spin %s for %s at %s" % (opts['object'], self.unit(opts['duration']),
                                         self.unit(opts['acceleration']))
    def spread(self, opts):
        return ["Spread %s of bacteria from well %s of %s "
               "to well %s of agar plate %s" % (opts['volume'], self.well(opts['from']),
                self.platename(opts['from']), self.well(opts['to']), self.platename(opts['to']))]

    def stamp(self, opts):
        stamps = []
        for t in opts['transfers']:
            stamps.append("Transfer from %s quadrant %s to %s quadrant %s" %
                          (self.platename(t['from']), self.well(t['from']),
                           self.platename(t['to']), self.well(t['to']))
                          )
        return stamps

    def thermocycle(self, opts):
        return "Thermocycle %s" % opts['object']

    def pipette(self, opts):
        pipettes = []
        for g in opts['groups']:
            for pip in g:
                if pip == "mix":
                    for m in g[pip]:
                        pipettes.append("Mix well %s of plate %s %d times with "
                                        "a volume of %s" % (self.well(m['well']),
                                                           self.platename(m['well']),
                                                           m['repetitions'], self.unit(m['volume'])))
                elif pip == "transfer":
                    pipettes.extend(["Transfer %s from %s "
                                     "to %s %s" %
                                     (self.unit(p['volume']),
                                      p['from'],
                                      p['to'],
                                      ("with one tip" if len(g[pip]) > 1 else "")
                                      ) for p in g[pip]
                                    ])
                elif pip == "distribute":
                    pipettes.append("Distribute from %s into %s" %
                                    (g[pip]['from'],
                                     self.well_list([d['well'] for
                                                d in g[pip]['to']], 20)))
                elif pip == "consolidate":
                    pipettes.append("Consolidate %s into %s" % (self.well_list([c['well'] for c in g[pip]['from']], 20), g[pip]['to']))
        return pipettes


    def uncover(self, opts):
        return "Uncover %s" % opts['object']

    def unseal(self, opts):
        return "Unseal %s" % opts['object']

    @staticmethod
    def platename(ref):
        return ref.split('/')[0]

    @staticmethod
    def well(ref):
        return ref.split('/')[1]

    @staticmethod
    def well_list(wells, max=10):
        well_list = "wells " + (', ').join(str(x) for x in wells)
        if len(wells) > max:
            well_list = str(len(wells)) + " wells"
        return well_list

    @staticmethod
    def unit(u):
        value = u.split(':')[0]
        unit = u.split(':')[1]
        return "%s %s" % (value, (unit + "s" if (float(value) > 1 and
                                                 unit in PLURAL_UNITS) else unit))

