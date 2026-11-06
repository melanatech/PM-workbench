"""Generated Altair theme register for neutral. Do not edit."""
import json

_CONFIG = json.loads("{\"config\": {\"background\": \"#FFFFFF\", \"font\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"view\": {\"stroke\": \"transparent\"}, \"axis\": {\"labelColor\": \"#1A1A1A\", \"titleColor\": \"#1A1A1A\", \"labelFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"titleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"gridColor\": \"#E0E0E0\", \"domainColor\": \"#1A1A1A\", \"tickColor\": \"#1A1A1A\"}, \"legend\": {\"labelColor\": \"#1A1A1A\", \"titleColor\": \"#1A1A1A\", \"labelFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"titleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\"}, \"title\": {\"color\": \"#1A1A1A\", \"subtitleColor\": \"#595959\", \"font\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"subtitleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\"}, \"range\": {\"category\": [\"#E69F00\", \"#56B4E9\", \"#009E73\", \"#F0E442\", \"#0072B2\", \"#D55E00\", \"#CC79A7\", \"#000000\"], \"heatmap\": [\"#EFF3FF\", \"#C6DBEF\", \"#9ECAE1\", \"#6BAED6\", \"#3182BD\", \"#08519C\"], \"diverging\": [\"#B2182B\", \"#EF8A62\", \"#FDDBC7\", \"#F7F7F7\", \"#D1E5F0\", \"#67A9CF\", \"#2166AC\"]}}}")


def config():
    return _CONFIG


def register():
    import altair as alt

    alt.themes.register("neutral", config)
    return config
