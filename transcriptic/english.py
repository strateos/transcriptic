from __future__ import print_function
from builtins import str
from builtins import object

PLURAL_UNITS = ["microliter", "nanoliter", "milliliter", "second", "minute",
                "hour", "g", "nanometer"]

TEMP_DICT = {"cold_20": "-20 degrees celsius",
             "cold_80": "-80 degrees celsius",
             "warm_37": "37 degrees celsius", "cold_4": "4 degrees celsius",
             "warm_30": "30 degrees celsius", "ambient": "room temperature"}


class AutoprotocolParser(object):

    def __init__(self, protocol_obj, parsed_output=None):
        self.parse(protocol_obj)

    def parse(self, obj):
        self.instructions = obj['instructions']
        self.refs = obj['refs']
        parsed_output = []
        for i in self.instructions:
            try:
                output = getattr(self, i['op'])(i)
                parsed_output.extend(output) if isinstance(
                    output, list) else parsed_output.append(output)
            except AttributeError:
                parsed_output.append("[Unknown instruction]")
        for i, p in enumerate(parsed_output):
            print("%d. %s" % (i + 1, p))
    # add a graph maker and maybe take out the integer count for each step...?

    def absorbance(self, opts):
        return ("Measure absorbance at %s for %s of plate %s" %
                (self.unit(opts['wavelength']),
                 self.well_list(opts['wells']),
                 opts['object']))

    def acoustic_transfer(self, opts):
        transfers = []
        for t in opts['groups'][0]['transfer']:
            transfers.append("Acoustic transfer %s from %s to %s" %
                             (self.unit(t["volume"]), t["from"], t["to"]))
        return transfers

    def autopick(self, opts):
        picks = []
        for i, g in enumerate(opts['groups']):
            picks.extend(["Pick %s colonies from %s %s: %s to %s, %s" %
                          (len(g["to"]), len(g['from']),
                           ("well" if len(g['from']) is 1 else "wells"),
                           self.well_list(g['from']),
                           self.well_list(g['to']),
                           ("data saved at '%s'" % opts["dataref"]
                            if i is 0 else "analyzed with previous"))])
        return picks

    @staticmethod
    def cover(opts):
        return "Cover %s with a %s lid" % (opts['object'], opts['lid'])

    # @staticmethod
    # def dispense(opts):
    #     return "Dispense %s to %d column(s) of %s" % (opts['reagent'],
    #                                                   len(opts['columns']),
    #                                                   opts['object'])

    # ----- Gautam's edits 6/7 -----
    def dispense(self, opts):
        unique_vol = []
        for col in opts['columns']:
            vol = self.unit(col["volume"])
            if vol not in unique_vol:
                unique_vol.append(vol)

        if len(opts['columns']) == 12 and len(unique_vol) == 1:
            return "Dispense %s of %s to the full plate of %s" % (unique_vol[0], opts['reagent'], opts['object'])
        else:
            return "Dispense corresponding amounts of %s to %d column(s) of %s" % (opts['reagent'], len(opts['columns']), opts['object'])
    # ------------------------------

    def flash_freeze(self, opts):
        return ("Flash freeze %s for %s" %
                (opts['object'], self.unit(opts['duration'])))

    def fluorescence(self, opts):
        return ("Read fluorescence of %s of plate %s at excitation wavelength "
                "%s and emission wavelength %s" %
                (self.well_list(opts['wells']),
                 opts['object'],
                 self.unit(opts['excitation']),
                 self.unit(opts['emission'])))

    def gel_separate(self, opts):
        return ("Perform gel electrophoresis using "
                "a %s agarose gel for %s" % (opts['matrix'].split(',')[1][:-1],
                                             self.unit(opts['duration'])))

    # ----- Gautam's edits 6/7 -----
    @staticmethod
    def gel_purify(opts):
        unique_bl = []
        for ext in opts['extract']:
            bl = ext["band_size_range"]
            if bl not in unique_bl:
                unique_bl.append(bl)
        for i in range(len(unique_bl)):
            unique_bl[i] = str(unique_bl[i]['min_bp']) + \
                "-" + str(unique_bl[i]['max_bp'])

        if len(unique_bl) <= 3:
            return "Perform gel purification on the %s agarose gel with band range(s) %s" % (opts['matrix'].split(',')[1][:-1], ', '.join(unique_bl))
        else:
            return "Perform gel purification on the %s agarose gel with %s band ranges" % (opts['matrix'].split(',')[1][:-1], len(unique_bl))

    # ------------------------------

    def incubate(self, opts):
        shaking = " (shaking)" if opts['shaking'] else ""
        return "Incubate %s at %s for %s%s" % (opts['object'],
                                               TEMP_DICT[opts['where']],
                                               self.unit(opts['duration']),
                                               shaking)

    @staticmethod
    def image_plate(opts):
        return "Take an image of %s" % opts['object']

    def luminescence(self, opts):
        return ("Read luminescence of %s of plate %s" % (self.well_list(opts['wells']), opts['object']))

    @staticmethod
    def oligosynthesize(opts):
        return (["Oligosynthesize sequence '%s' into '%s'" % (o['sequence'], o['destination']) for o in opts['oligos']])

    def provision(self, opts):
        provisions = []
        for t in opts['to']:
            provisions.append("Provision %s of resource with ID %s to well %s of container %s" %
                              (self.unit(t['volume']), opts['resource_id'],
                               self.well(t['well']), self.platename(t['well'])
                               ))
        return provisions

    def sanger_sequence(self, opts):
        seq = "Sanger sequence %s of plate %s" % (
            self.well_list(opts['wells']), opts['object'])
        if opts['type'] == "standard":
            return seq
        elif opts['type'] == "rca":
            return seq + " with %s" % self.platename(opts['primer'])

    # ----- Gautam's edits 6/7 -----
    def get_unique_wells(self, list_of_wells):
        unique_wells = []
        for well in list_of_wells:
            w = well['object']
            if w not in unique_wells:
                unique_wells.append(w)
        return unique_wells

    def illumina_sequence(self, opts):
        unique_wells = self.get_unique_wells(opts['lanes'])
        unique_plates = self.get_unique_plates(unique_wells)

        if len(unique_plates) == 1 and len(unique_wells) <= 3:
            seq = "Illumina sequence wells %s" % (", ".join(unique_wells))
        elif len(unique_plates) > 1 and len(unique_plates) <= 3:
            seq = "Illumina sequence the corresponding wells of plates %s" % ", ".join(
                unique_plates[0])
        else:
            seq = "Illumina sequence the corresponding wells of %s plates" % len(
                unique_wells)

        return seq + " with library size %s" % opts['library_size']

    @staticmethod
    def flow_analyze(opts):
        wells = []
        for sample in opts['samples']:
            if sample['well'] not in wells:
                wells.append(sample['well'])

        return "Perform flow cytometry on %s with the respective FSC and SSC channel parameters" % ", ".join(wells)
    # ------------------------------

    @staticmethod
    def seal(opts):
        return "Seal %s (%s)" % (opts['object'], opts['type'])

    def spin(self, opts):
        return ("Spin %s for %s at %s" %
                (opts['object'], self.unit(opts['duration']),
                 self.unit(opts['acceleration'])))

    def spread(self, opts):
        return ["Spread %s of bacteria from well %s of %s "
                "to well %s of agar plate %s" %
                (opts['volume'], self.well(opts['from']),
                 self.platename(opts['from']), self.well(opts['to']),
                 self.platename(opts['to']))]

    def stamp(self, opts):
        stamps = []
        for g in opts['groups']:
            for pip in g:
                if pip == "transfer":
                    stamps.extend(["Stamp %s from source origin %s "
                                   "to destination origin %s %s (%s)" %
                                   (self.unit(p['volume']),
                                    p['from'],
                                    p['to'],
                                    ("with the same set of tips as previous" if
                                     (len(g[pip]) > 1 and i > 0) else ""),
                                    ("%s rows x %s columns" %
                                     (g['shape']['rows'],
                                      g['shape']['columns']))
                                    ) for i, p in enumerate(g[pip])
                                   ])
        return stamps

    @staticmethod
    def thermocycle(opts):
        return "Thermocycle %s" % opts['object']

    def pipette(self, opts):
        pipettes = []
        for g in opts['groups']:
            for pip in g:
                if pip == "mix":
                    for m in g[pip]:
                        pipettes.append("Mix well %s of plate %s %d times "
                                        "with a volume of %s" %
                                        (self.well(m['well']),
                                         self.platename(
                                            m['well']),
                                            m['repetitions'],
                                            self.unit(m['volume']))
                                        )
                elif pip == "transfer":
                    pipettes.extend(["Transfer %s from %s "
                                     "to %s %s" %
                                     (self.unit(p['volume']),
                                      p['from'],
                                      p['to'],
                                      ("with the same tip as previous" if (
                                          len(g[pip]) > 1 and i > 0) else "")
                                      ) for i, p in enumerate(g[pip])
                                     ])
                elif pip == "distribute":
                    pipettes.append("Distribute from %s into %s" %
                                    (g[pip]['from'],
                                     self.well_list([d['well'] for
                                                     d in g[pip]['to']], 20)))
                elif pip == "consolidate":
                    pipettes.append("Consolidate %s into %s" %
                                    (self.well_list([c['well'] for c in
                                                     g[pip]['from']], 20),
                                     g[pip]['to']))
        return pipettes

    # ----- Gautam's edits 6/7 -----
    def magnetic_transfer(self, opts):
        # dry, incubate, collect, release, mix
        specific_op = list(opts['groups'][0][0].keys())[0]
        specs_dict = opts['groups'][0][0][specific_op]
        seq = "Magnetically %s %s" % (specific_op, specs_dict["object"])

        if specific_op == "dry":
            return seq + " for %s" % self.unit(specs_dict["duration"])
        elif specific_op == "incubate":
            return seq + " for %s with a tip position of %s" % (self.unit(specs_dict["duration"]), specs_dict["tip_position"])
        elif specific_op == "collect":
            return seq + " beads for %s cycles with a pause duration of %s" % (specs_dict["cycles"], self.unit(specs_dict["pause_duration"]))
        elif specific_op == "release" or "mix":
            return seq + " beads for %s at an aplitude of %s" % (self.unit(specs_dict["duration"]), specs_dict["amplitude"])

    def get_unique_plates(self, list_of_wells):
        unique_plates = []
        for well in list_of_wells:
            loc = well.find('/')
            if loc == -1:
                plate = well
            else:
                plate = well[:loc]

            if plate not in unique_plates:
                unique_plates.append(plate)
        return unique_plates

    def measure_volume(self, opts):
        unique_plates = self.get_unique_plates(opts['object'])
        if len(unique_plates) <= 3:
            return "Mesaure volume of %s wells from %s" % (len(opts['object']), ", ".join(unique_plates))
        else:
            return "Mesaure volume of %s wells from the %s plates" % (len(opts['object']), len(unique_plates))

    def measure_mass(self, opts):
        return "Measure mass of %s" % ", ".join(opts['object'])

    def measure_concentration(self, opts):
        return "Measure concentration of %s %s source aliquots" % (self.unit(opts['volume']), opts['measurement'])
    # ------------------------------

    @staticmethod
    def uncover(opts):
        return "Uncover %s" % opts['object']

    @staticmethod
    def unseal(opts):
        return "Unseal %s" % opts['object']

    @staticmethod
    def platename(ref):
        return ref.split('/')[0]

    @staticmethod
    def well(ref):
        return ref.split('/')[1]

    @staticmethod
    def well_list(wells, max_len=10):
        well_list = "wells " + (', ').join(str(x) for x in wells)
        if len(wells) > max_len:
            well_list = str(len(wells)) + " wells"
        return well_list

    @staticmethod
    def unit(u):
        value = u.split(':')[0]
        unit = u.split(':')[1]
        return ("%s %s" % (value,
                           (unit + "s" if (float(value) > 1 and
                                           unit in PLURAL_UNITS) else unit))
                )
