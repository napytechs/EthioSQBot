from utils.filters import parse_time, smart_subject as smart_hash_subject
import unittest
import time


class CustomTestCase(unittest.TestCase):
    def test_each_subject(self):
        self.assertEqual("#አማርኛ", smart_hash_subject("🇪🇹 አማርኛ"))
        self.assertEqual("#አፋን_ኦሮሞ", smart_hash_subject("🇪🇹 አፋን ኦሮሞ"))
        self.assertEqual("#ኢንግሊሽ", smart_hash_subject("🇬🇧 ኢንግሊሽ"))
        self.assertEqual("#ኬሚስትሪ", smart_hash_subject("🧪 ኬሚስትሪ"))
        self.assertEqual("#ሒሳብ", smart_hash_subject("🧮 ሒሳብ"))
        self.assertEqual("#ፊዚክስ", smart_hash_subject("🔭 ፊዚክስ"))
        self.assertEqual("#ስነህይወት", smart_hash_subject("🔬 ስነህይወት|Biology"))
        self.assertEqual("#ስነህይወት", smart_hash_subject("🔬 ስነህይወት | Biology"))
        self.assertEqual("#ስነህይወት", smart_hash_subject("🔬 ስነህይወት"))
        self.assertEqual("#ታሪክ", smart_hash_subject("🌏 ታሪክ"))
        self.assertEqual("#ጂኦግራፊ", smart_hash_subject("🧭 ጂኦግራፊ"))
        self.assertEqual("#ስነዜጋ", smart_hash_subject("⚖ ስነዜጋ|Civics"))
        self.assertEqual("#ስነዜጋ", smart_hash_subject("⚖ ስነዜጋ | Civics"))
        self.assertEqual("#ስነዜጋ", smart_hash_subject("⚖ ስነዜጋ"))
        self.assertEqual("#ስነብዕል", smart_hash_subject("💶 ስነብዕል|Economics"))
        self.assertEqual("#ስነብዕል", smart_hash_subject("💶 ስነብዕል | Economics"))
        self.assertEqual("#ስነብዕል", smart_hash_subject("💶 ስነብዕል"))
        self.assertEqual("#ቢዝነስ", smart_hash_subject("💰 ቢዝነስ"))
        self.assertEqual("#ህብረተስብ", smart_hash_subject("👥 ህብረተስብ|Social"))
        self.assertEqual("#ህብረተስብ", smart_hash_subject("👥 ህብረተስብ | Social"))
        self.assertEqual("#ህብረተስብ", smart_hash_subject("👥 ህብረተስብ"))
        self.assertEqual("#ጠቅላላ_እውቀት", smart_hash_subject("🧠 ጠቅላላ እውቀት"))


class TestTime(unittest.TestCase):
    def test_time(self):
        self.assertEqual("አሁን", parse_time(time.time()))
        self.assertEqual("ከ30 ሰከንድ በፊት", parse_time(time.time() - 30))
        self.assertEqual("ከ2 ደቂቃዎች በፊት", parse_time(time.time() - 120))
        self.assertEqual("ከ2 ሰዓታት በፊት", parse_time(time.time() - 2*3600))


if __name__ == '__main__':
    unittest.main()
