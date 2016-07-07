import pytest
import unittest
import json
from autoprotocol.protocol import Protocol
from autoprotocol.unit import Unit
from transcriptic import english


class AP2EnTestCase(unittest.TestCase):

    def test_web_example(self):

        p = Protocol()

        bacterial_sample = p.ref("bacteria", None, "micro-1.5", discard=True)
        test_plate = p.ref("test_plate", None, "96-flat", storage="cold_4")

        p.dispense_full_plate(test_plate, "lb-broth-noAB", "50:microliter")
        w = 0
        amt = 1
        while amt < 20:
            p.transfer(bacterial_sample.well(
                0), test_plate.well(w), "%d:microliter" % amt)
            amt += 2
            w += 1

        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(forest, [[1], [2], [3], [4], [5], [
                         6], [7], [8], [9], [10], [11]])

    def test_med_json_job_tree(self):

        pjsonString = """{
              "refs": {
                "3-384-pcr": {
                  "new": "384-pcr", 
                  "discard": true
                }, 
                "5-384-pcr": {
                  "new": "384-pcr", 
                  "discard": true
                }, 
                "4-384-pcr": {
                  "new": "384-pcr", 
                  "discard": true
                }, 
                "1-384-pcr": {
                  "new": "384-pcr", 
                  "discard": true
                }, 
                "0-384-pcr": {
                  "new": "384-pcr", 
                  "discard": true
                }, 
                "6-384-pcr": {
                  "new": "384-pcr", 
                  "discard": true
                }, 
                "2-384-pcr": {
                  "new": "384-pcr", 
                  "discard": true
                }
              }, 
              "instructions": [
                {
                  "groups": [
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "3-384-pcr/383", 
                          "from": "3-384-pcr/0"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "3-384-pcr/382", 
                          "from": "3-384-pcr/1"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "5-384-pcr/383", 
                          "from": "5-384-pcr/0"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "5-384-pcr/382", 
                          "from": "5-384-pcr/1"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "4-384-pcr/383", 
                          "from": "4-384-pcr/0"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "4-384-pcr/382", 
                          "from": "4-384-pcr/1"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "1-384-pcr/383", 
                          "from": "1-384-pcr/0"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "1-384-pcr/382", 
                          "from": "1-384-pcr/1"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "0-384-pcr/383", 
                          "from": "0-384-pcr/0"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "0-384-pcr/382", 
                          "from": "0-384-pcr/1"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "6-384-pcr/383", 
                          "from": "6-384-pcr/0"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "6-384-pcr/382", 
                          "from": "6-384-pcr/1"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "2-384-pcr/383", 
                          "from": "2-384-pcr/0"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }, 
                    {
                      "transfer": [
                        {
                          "volume": "10.0:microliter", 
                          "to": "2-384-pcr/382", 
                          "from": "2-384-pcr/1"
                        }
                      ], 
                      "x_tip_type": "filtered50"
                    }
                  ], 
                  "op": "pipette"
                }
              ]
            }
            """
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(forest, [[1, [2]], [3, [4]], [5, [6]], [
            7, [8]], [9, [10]], [11, [12]], [13, [14]]])

    def test_large_json_parse(self):
        with open("test/autoprotocol/longrun.json") as json_file:
            pjson = json.load(json_file)
            parser_instance = english.AutoprotocolParser(pjson)
            # Not running job_tree() on this due to size

            # parser_instance.job_tree()
            # parsed_output = parser_instance.parsed_output
            # steps = parser_instance.object_list
            # forest = parser_instance.forest_list
            # Desired: no ["Unkown Instruction"] prints

    def test_measure_suite(self):
        """
        Desired Output:
        1. Measure concentration of 2.0 microliters DNA source aliquots
        2. Measure mass of test_plate2
        3. Measure volume of 12 wells from test_plate
        4. Measure volume of 8 wells from test_plate2
        """

        p = Protocol()
        test_plate = p.ref("test_plate", None, "96-flat", storage="cold_4")
        test_plate2 = p.ref("test_plate2", id=None,
                            cont_type="96-flat", storage=None, discard=True)
        for well in test_plate2.all_wells():
            well.set_volume("150:microliter")

        p.measure_concentration(wells=test_plate2.wells_from(
            0, 96), dataref="mc_test", measurement="DNA", volume=Unit(2, "microliter"))
        p.measure_mass(test_plate2, "test_ref")
        p.measure_volume(test_plate.wells_from(0, 12), "test_ref")
        p.measure_volume(test_plate2.wells_from(1, 8), "test_ref2")

        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output, ["Measure concentration of 2.0 microliters DNA source aliquots of test_plate2",
                            "Measure mass of test_plate2",
                            "Measure volume of 12 wells from test_plate",
                            "Measure volume of 8 wells from test_plate2"])
        self.assertEqual(forest, [[1, [2, [4]]], [3]])

    def test_mag_incubate(self):
        """
        Desired Output:
        1. Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0
        2. Distribute from test/1 into wells test/7, test/8, test/9
        3. Distribute from test/2 into wells test/10
        4. Distribute from test/0 into wells test/1
        5. Magnetically incubate pcr_0 for 30.0 minutes with a tip position of 1.5
        """

        p = Protocol()
        pcrs = [p.ref("pcr_%s" % i, None, "96-pcr", storage="cold_20")
                for i in range(7)]
        pcr = pcrs[0]

        p.mag_release("96-pcr", pcr, "30:second", "1:hertz",
                      center=float(5) / 100, amplitude=0)

        c = p.ref("test", None, "96-flat", discard=True)
        srcs = c.wells_from(1, 2).set_volume("100:microliter")
        dests = c.wells_from(7, 4)
        p.distribute(srcs, dests, "30:microliter", allow_carryover=True)
        p.distribute(c.well("A1").set_volume(
            "20:microliter"), c.well("A2"), "5:microliter")

        p.mag_incubate("96-pcr", pcr, "30:minute",
                       temperature="30:celsius")

        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output, ["Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0",
                            "Distribute from test/1 into wells test/7, test/8, test/9",
                            "Distribute from test/2 into wells test/10",
                            "Distribute from test/0 into wells test/1",
                            "Magnetically incubate pcr_0 for 30.0 minutes with a tip position of 1.5"])
        self.assertEqual(forest, [[1, [5]], [2, [4]], [3]])

    def test_mag_mix(self):
        """
        Desired Output:
        1. Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0
        2. Distribute from test/1 into wells test/7, test/8, test/9
        3. Distribute from test/2 into wells test/10
        4. Distribute from test/0 into wells test/1
        5. Magnetically mix pcr_0 beads for 30.0 seconds at an amplitude of 0
        """

        p = Protocol()
        pcrs = [p.ref("pcr_%s" % i, None, "96-pcr", storage="cold_20")
                for i in range(7)]
        pcr = pcrs[0]

        p.mag_release("96-pcr", pcr, "30:second", "1:hertz",
                      center=float(5) / 100, amplitude=0)

        c = p.ref("test", None, "96-flat", discard=True)
        srcs = c.wells_from(1, 2).set_volume("100:microliter")
        dests = c.wells_from(7, 4)
        p.distribute(srcs, dests, "30:microliter", allow_carryover=True)
        p.distribute(c.well("A1").set_volume(
            "20:microliter"), c.well("A2"), "5:microliter")

        p.mag_mix("96-pcr", pcr, "30:second", "60:hertz",
                  center=float(100) / 100, amplitude=0)

        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output, ["Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0",
                            "Distribute from test/1 into wells test/7, test/8, test/9",
                            "Distribute from test/2 into wells test/10",
                            "Distribute from test/0 into wells test/1",
                            "Magnetically mix pcr_0 beads for 30.0 seconds at an amplitude of 0"])
        self.assertEqual(forest, [[1, [5]], [2, [4]], [3]])

    def test_mag_dry(self):
        """
        Desired Output:
        1. Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0
        2. Distribute from test/1 into wells test/7, test/8, test/9
        3. Distribute from test/2 into wells test/10
        4. Distribute from test/0 into wells test/1
        5. Magnetically dry pcr_0 for 30.0 minutes
        """

        p = Protocol()
        pcrs = [p.ref("pcr_%s" % i, None, "96-pcr", storage="cold_20")
                for i in range(7)]
        pcr = pcrs[0]

        p.mag_release("96-pcr", pcr, "30:second", "1:hertz",
                      center=float(5) / 100, amplitude=0)

        c = p.ref("test", None, "96-flat", discard=True)
        srcs = c.wells_from(1, 2).set_volume("100:microliter")
        dests = c.wells_from(7, 4)
        p.distribute(srcs, dests, "30:microliter", allow_carryover=True)
        p.distribute(c.well("A1").set_volume(
            "20:microliter"), c.well("A2"), "5:microliter")

        p.mag_dry("96-pcr", pcr, "30:minute",
                  new_tip=False, new_instruction=False)

        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output, ["Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0",
                            "Distribute from test/1 into wells test/7, test/8, test/9",
                            "Distribute from test/2 into wells test/10",
                            "Distribute from test/0 into wells test/1",
                            "Magnetically dry pcr_0 for 30.0 minutes"])
        self.assertEqual(forest, [[1, [5]], [2, [4]], [3]])

    def test_mag_collect(self):
        """
        Desired Output:
        1. Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0
        2. Distribute from test/1 into wells test/7, test/8, test/9
        3. Distribute from test/2 into wells test/10
        4. Distribute from test/0 into wells test/1
        5. Magnetically collect pcr_0 beads for 5 cycles with a pause duration of 30.0 seconds
        """

        p = Protocol()
        pcrs = [p.ref("pcr_%s" % i, None, "96-pcr", storage="cold_20")
                for i in range(7)]
        pcr = pcrs[0]

        p.mag_release("96-pcr", pcr, "30:second", "1:hertz",
                      center=float(5) / 100, amplitude=0)

        c = p.ref("test", None, "96-flat", discard=True)
        srcs = c.wells_from(1, 2).set_volume("100:microliter")
        dests = c.wells_from(7, 4)
        p.distribute(srcs, dests, "30:microliter", allow_carryover=True)
        p.distribute(c.well("A1").set_volume(
            "20:microliter"), c.well("A2"), "5:microliter")

        p.mag_collect("96-pcr", pcr, 5, "30:second",
                      bottom_position=float(5) / 100)

        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output, ["Magnetically release pcr_0 beads for 30.0 seconds at an amplitude of 0",
                            "Distribute from test/1 into wells test/7, test/8, test/9",
                            "Distribute from test/2 into wells test/10",
                            "Distribute from test/0 into wells test/1",
                            "Magnetically collect pcr_0 beads for 5 cycles with a pause duration of 30.0 seconds"])
        self.assertEqual(forest, [[1, [5]], [2, [4]], [3]])

    def test_purify(self):
        """
        Desired Output:
        1. Perform gel purification on the 0.8% agarose gel with band range(s) 0-10
        2. Perform gel purification on the 0.8% agarose gel with band range(s) 0-10
        3. Perform gel purification on the 0.8% agarose gel with band range(s) 0-10
        """

        p = Protocol()
        sample_wells = p.ref("sample_wells", None, "96-pcr",
                             discard=True).wells_from(0, 20)
        extract_wells = [p.ref("extract_%s" % i, None, "micro-1.5",
                               storage="cold_4").well(0) for i in sample_wells]
        extract = [
            {
                "source": sample_wells[i],
                "band_list": [{
                    "band_size_range": {"min_bp": 0, "max_bp": 10},
                    "elution_volume": Unit("5:microliter"),
                    "elution_buffer": "water",
                    "destination": d
                }],
                "lane": None,
                "gel": None
            } for i, d in enumerate(extract_wells)
        ]

        p.gel_purify(extract, "10:microliter",
                     "size_select(8,0.8%)", "ladder1", "gel_purify_test")

        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output, ["Perform gel purification on the 0.8% agarose gel with band range(s) 0-10",
                            "Perform gel purification on the 0.8% agarose gel with band range(s) 0-10",
                            "Perform gel purification on the 0.8% agarose gel with band range(s) 0-10"])
        self.assertEqual(forest, [[1, [2, [3]]]])

    def test_dispense_suite(self):
        """
        Desired Output:
        1. Dispense 100 microliters of water to the full plate of sample_plate5
        2. Dispense corresponding amounts of water to 12 column(s) of sample_plate5
        """

        p = Protocol()
        sample_plate5 = p.ref("sample_plate5", None,
                              "96-flat", storage="warm_37")

        p.dispense_full_plate(sample_plate5, "water", "100:microliter")
        p.dispense(sample_plate5,
                   "water",
                   [{"column": 0, "volume": "10:microliter"},
                    {"column": 1, "volume": "20:microliter"},
                    {"column": 2, "volume": "30:microliter"},
                    {"column": 3, "volume": "40:microliter"},
                    {"column": 4, "volume": "50:microliter"},
                    {"column": 5, "volume": "60:microliter"},
                    {"column": 6, "volume": "70:microliter"},
                    {"column": 7, "volume": "80:microliter"},
                    {"column": 8, "volume": "90:microliter"},
                    {"column": 9, "volume": "100:microliter"},
                    {"column": 10, "volume": "110:microliter"},
                    {"column": 11, "volume": "120:microliter"}
                    ])
        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output, ["Dispense 100 microliters of water to the full plate of sample_plate5",
                            "Dispense corresponding amounts of water to 12 column(s) of sample_plate5"])
        self.assertEqual(forest, [[1, [2]]])

    def test_illumina(self):
        """
        Desired Output:
        1. Illumina sequence wells test_plate6/0, test_plate6/1 with library size 34
        """

        p = Protocol()
        sample_wells6 = p.ref(
            "test_plate6", None, "96-pcr", discard=True).wells_from(0, 8)
        p.illuminaseq("PE", [{"object": sample_wells6[0], "library_concentration": 1.0},
                             {"object": sample_wells6[1], "library_concentration": 2}],
                      "nextseq", "mid", 'none', 34, "dataref")
        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output, ["Illumina sequence wells test_plate6/0, test_plate6/1 with library size 34"])
        self.assertEqual(forest, [[1]])

    def test_flow(self):
        """
        Desired Output:
        1. Perform flow cytometry on well0 with the respective FSC and SSC channel parameters
        """

        p = Protocol()
        dataref = "test_ref"
        well0 = p.ref("test_plate", None, "96-pcr",
                      discard=True).well(0)
        FSC = {"voltage_range": {"low": "230:volt", "high": "280:volt"},
               "area": True, "height": True, "weight": False}
        SSC = {"voltage_range": {"low": "230:volt", "high": "280:volt"},
               "area": True, "height": True, "weight": False}
        channel0 = [FSC, SSC]
        neg_controls = [{"well": well0, "volume": "100:microliter",
                         "captured_events": 5, "channel": channel0}]
        samples = [{"well": well0,
                    "volume": "100:microliter", "captured_events": 9}]

        p.flow_analyze(dataref, FSC, SSC, neg_controls,
                       samples)

        pjsonString = json.dumps(p.as_dict(), indent=2)
        pjson = json.loads(pjsonString)
        parser_instance = english.AutoprotocolParser(pjson)
        parser_instance.job_tree()

        parsed_output = parser_instance.parsed_output
        steps = parser_instance.object_list
        forest = parser_instance.forest_list

        self.assertEqual(
            parsed_output, ["Perform flow cytometry on test_plate/0 with the respective FSC and SSC channel parameters"])
        self.assertEqual(forest, [[1]])
