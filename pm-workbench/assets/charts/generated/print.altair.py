"""Generated Altair theme register for print. Do not edit."""
import json

_CONFIG = json.loads("{\"config\": {\"background\": \"#FFFFFF\", \"font\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"view\": {\"stroke\": \"transparent\"}, \"axis\": {\"labelColor\": \"#000000\", \"titleColor\": \"#000000\", \"labelFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"titleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"gridColor\": \"#6B6B6B\", \"domainColor\": \"#000000\", \"tickColor\": \"#000000\"}, \"legend\": {\"labelColor\": \"#000000\", \"titleColor\": \"#000000\", \"labelFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"titleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\"}, \"title\": {\"color\": \"#000000\", \"subtitleColor\": \"#333333\", \"font\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"subtitleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\"}, \"range\": {\"category\": [\"#E69F00\", \"#56B4E9\", \"#009E73\", \"#F0E442\", \"#0072B2\", \"#D55E00\", \"#CC79A7\", \"#000000\"], \"heatmap\": [\"#F7F7F7\", \"#D9D9D9\", \"#BDBDBD\", \"#969696\", \"#636363\", \"#252525\"], \"diverging\": [\"#B2182B\", \"#EF8A62\", \"#FDDBC7\", \"#FFFFFF\", \"#E0E0E0\", \"#999999\", \"#4D4D4D\"]}}}")


def config():
    return _CONFIG


def register():
    import altair as alt

    alt.themes.register("print", config)
    return config
