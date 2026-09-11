"""Host checks: C++ recorder bytes -> independent Python decoder + migration."""
import csv
import importlib.util
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
FIRMWARE = ROOT / "firmware/imu_raw_stream"
spec = importlib.util.spec_from_file_location("decoder", ROOT / "experiments/decode_motion_log.py")
decoder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(decoder)


class OfflineLogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        cls.hour = cls.directory / "hour.bin"
        exe = cls.directory / "codec-test"
        compiler = shutil.which("c++") or shutil.which("clang++")
        subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror",
                        "-I", str(FIRMWARE / "src"),
                        str(FIRMWARE / "tests/motion_format_test.cpp"), "-o", str(exe)], check=True)
        subprocess.run([str(exe), str(cls.hour)], check=True)
        cls.data = cls.hour.read_bytes()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_one_hour_roundtrip(self):
        output = self.directory / "hour.csv"
        result = decoder.convert(self.hour, output)
        self.assertEqual(result["records"], 72000)
        self.assertEqual(result["last_elapsed_ms"], 3600000)
        self.assertEqual(result["start_unix_ms"], 1788969600000)
        self.assertEqual(result["warnings"], [])
        with output.open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["elapsed_ms"], "50")
        self.assertEqual(rows[0]["ax_g"], "-3.997696")
        self.assertEqual(rows[0]["temp_c"], "24.0000")
        self.assertEqual(rows[35999]["state"], "Resting")
        self.assertEqual(rows[36000]["state"], "Active")

    def test_interruption_at_every_tail_byte(self):
        for cut in range(24):
            path = self.directory / "interrupted.bin"
            path.write_bytes(self.data[:32 + 100*24 + cut])
            result = decoder.convert(path, self.directory / "interrupted.csv")
            self.assertEqual(result["records"], 100)
            self.assertEqual(result["trailing_bytes"], cut)

    def test_crc_failure_does_not_replace_existing_export(self):
        corrupt = bytearray(self.data[:32+120*24])
        corrupt[32+50*24+10] ^= 1
        source, output = self.directory / "corrupt.bin", self.directory / "safe.csv"
        source.write_bytes(corrupt)
        output.write_text("keep existing export")
        with self.assertRaisesRegex(ValueError, "Invalid record 50"):
            decoder.convert(source, output)
        self.assertEqual(output.read_text(), "keep existing export")
        result = decoder.convert(source, output, recover_prefix=True)
        self.assertEqual(result["records"], 50)
        self.assertTrue(result["recovered_prefix"])

    def test_invalid_header_and_timestamp(self):
        bad = bytearray(self.data[:32+48])
        bad[0] ^= 1
        path = self.directory / "bad.bin"
        path.write_bytes(bad)
        with self.assertRaises(ValueError):
            decoder.convert(path, self.directory / "bad.csv")
        duplicate = self.data[:32+24] + self.data[32:32+24]
        path.write_bytes(duplicate)
        with self.assertRaisesRegex(ValueError, "Invalid record 1"):
            decoder.convert(path, self.directory / "bad.csv")
        with self.assertRaises(ValueError):
            decoder.convert(self.hour, self.hour)

    def test_old_partitions_preserved_and_new_partition_fits(self):
        expected = {"nvs":(0x9000,0x5000),"otadata":(0xe000,0x2000),
                    "app0":(0x10000,0x140000),"app1":(0x150000,0x140000),
                    "spiffs":(0x290000,0x160000),"coredump":(0x3f0000,0x10000),
                    "motion":(0x400000,0x400000)}
        actual = {}
        for line in (FIRMWARE / "partitions.csv").read_text().splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            fields = [x.strip() for x in line.split(",")]
            actual[fields[0]] = (int(fields[3],0),int(fields[4],0))
        self.assertEqual(actual, expected)
        end = 0
        for offset, size in sorted(actual.values()):
            self.assertGreaterEqual(offset, end)
            self.assertEqual(offset % 4096, 0)
            end = offset + size
        self.assertEqual(end, 8*1024*1024)
        # Validate the actual generated table as well when a firmware build exists.
        built = FIRMWARE / ".pio/build/adafruit_feather_esp32_v2/partitions.bin"
        if built.exists():
            entries = {}
            data = built.read_bytes()
            for pos in range(0,len(data),32):
                if data[pos:pos+2] != b"\xaa\x50":
                    continue
                _,_,_,offset,size,label,_ = struct.unpack("<HBBII16sI",data[pos:pos+32])
                entries[label.split(b"\0")[0].decode()] = (offset,size)
            self.assertEqual(entries, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
