import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "brain"))

import weather


def said(*turns):
    return [{"role": role, "content": text} for role, text in turns]


class WeatherRoutingTests(unittest.TestCase):
    def test_weather_questions_are_recognised(self):
        for prompt in ("whats the weather like", "is it going to rain tomorrow",
                       "do i need an umbrella", "how hot is it outside",
                       "whats the forecast for the weekend", "is it cold out",
                       "whats the temperature outside"):
            self.assertTrue(weather.asks_about_weather(prompt), prompt)

    def test_portuguese_weather_questions(self):
        for prompt in ("qual é a previsão do tempo para amanhã", "vai chover hoje", "está fazendo calor lá fora",
                       "preciso de guarda-chuva", "qual a temperatura lá fora"):
            self.assertTrue(weather.asks_about_weather(prompt), prompt)
        self.assertFalse(weather.asks_about_weather("qual temperatura uso para imprimir petg"))

    def test_other_temperatures_are_not_weather(self):
        for prompt in ("what temperature should i run petg at",
                       "what temperature does water boil at in fahrenheit",
                       "my nozzle is too hot", "cheers alfred", "what time is it"):
            self.assertFalse(weather.asks_about_weather(prompt), prompt)

    def test_follow_ups_stay_on_the_weather(self):
        history = said(("user", "whats the weather like"), ("assistant", "Seventy-eight."))
        for prompt in ("its 92 degrees where did you pull 78 from", "and tomorrow",
                       "what about saturday"):
            self.assertTrue(weather.asks_about_weather(prompt, history), prompt)

    def test_phrasings_from_the_first_voice_session(self):
        self.assertTrue(weather.asks_about_weather("what's the temp in santa fe"))
        self.assertEqual(weather.named_place("what's the temp in santa fe"), "santa fe")
        history = said(("user", "what's the weather like"), ("assistant", "Seventy-eight."))
        self.assertTrue(weather.asks_about_weather("as of when alfred i have it as 92", history))
        self.assertFalse(weather.asks_about_weather("whats the temperature in my enclosure"))

    def test_a_new_weather_question_does_not_inherit_the_place(self):
        history = said(("user", "whats the weather in chicago"), ("assistant", "Seventy."))
        calls = []
        saved = weather.geocode, weather.home, weather.forecast, weather.render
        weather.geocode = lambda place: calls.append(place) or ("There", 1.0, 2.0)
        weather.home = lambda: ("Home", 3.0, 4.0)
        weather.forecast = lambda latitude, longitude: None
        weather.render = lambda name, data: name
        try:
            self.assertEqual(weather.lookup("whats the weather like today", history), "Home")
            self.assertEqual(weather.lookup("and tomorrow", history), "There")
            self.assertEqual(calls, ["chicago"])
        finally:
            weather.geocode, weather.home, weather.forecast, weather.render = saved

    def test_follow_up_survives_a_correction_in_between(self):
        history = said(("user", "whats the weather like"), ("assistant", "Seventy-eight."),
                       ("user", "its 92 degrees where did you pull 78 from"),
                       ("assistant", "From the forecast."))
        self.assertTrue(weather.asks_about_weather("and tomorrow", history))

    def test_follow_up_needs_a_weather_question_before_it(self):
        history = said(("user", "how long should a steak rest"), ("assistant", "Five minutes."))
        self.assertFalse(weather.asks_about_weather("and tomorrow", history))

    def test_named_places(self):
        self.assertEqual(weather.named_place("whats the weather in chicago tomorrow"), "chicago")
        self.assertEqual(weather.named_place("whats the weather in new york like"), "new york")
        self.assertEqual(weather.named_place("forecast for denver this weekend?"), "denver")

    def test_times_and_errands_are_not_places(self):
        for prompt in ("will it rain in the morning", "will it rain in two hours",
                       "do i need an umbrella for class", "whats the weather like at the moment",
                       "whats the weather", "is it hot out today"):
            self.assertIsNone(weather.named_place(prompt), prompt)

    def test_render_speaks_degrees_and_says_it_is_current(self):
        data = {
            "current": {"time": "2026-09-16T17:00", "temperature_2m": 93.4,
                        "apparent_temperature": 99.6, "relative_humidity_2m": 41,
                        "weather_code": 0, "wind_speed_10m": 6.1},
            "daily": {"time": ["2026-09-16", "2026-09-17", "2026-09-18"],
                      "temperature_2m_max": [93.5, 94.3, 91.6],
                      "temperature_2m_min": [71.6, 71.6, 70.7],
                      "precipitation_probability_max": [23, 16, None],
                      "weather_code": [3, 3, 82]},
        }
        text = weather.render("Home", data)
        self.assertIn("Now: 93 degrees, feels like 100, clear", text)
        self.assertIn("Tomorrow: high 94, low 72, overcast, 16 percent chance of rain.", text)
        self.assertIn("Friday: high 92, low 71, violent showers.", text)
        self.assertIn("earlier figure was wrong", text)
        self.assertNotIn("°", text)


if __name__ == "__main__":
    unittest.main()
