"""Generated Altair theme register for high-contrast. Do not edit."""
import json

_CONFIG = json.loads("{\"config\": {\"background\": \"#FFFFFF\", \"font\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"view\": {\"stroke\": \"transparent\"}, \"axis\": {\"labelColor\": \"#000000\", \"titleColor\": \"#000000\", \"labelFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"titleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"gridColor\": \"#4D4D4D\", \"domainColor\": \"#000000\", \"tickColor\": \"#000000\"}, \"legend\": {\"labelColor\": \"#000000\", \"titleColor\": \"#000000\", \"labelFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"titleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\"}, \"title\": {\"color\": \"#000000\", \"subtitleColor\": \"#1A1A1A\", \"font\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"subtitleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\"}, \"range\": {\"category\": [\"#E69F00\", \"#56B4E9\", \"#009E73\", \"#F0E442\", \"#0072B2\", \"#D55E00\", \"#CC79A7\", \"#000000\"], \"heatmap\": [\"#C6DBEF\", \"#9ECAE1\", \"#6BAED6\", \"#3182BD\", \"#08519C\"], \"diverging\": [\"#B2182B\", \"#EF8A62\", \"#FDDBC7\", \"#F7F7F7\", \"#D1E5F0\", \"#67A9CF\", \"#2166AC\"]}}}")


def config():
    return _CONFIG


def register():
    import altair as alt

    alt.themes.register("high-contrast", config)
    return config
