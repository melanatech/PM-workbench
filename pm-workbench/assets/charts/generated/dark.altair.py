"""Generated Altair theme register for dark. Do not edit."""
import json

_CONFIG = json.loads("{\"config\": {\"background\": \"#141414\", \"font\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"view\": {\"stroke\": \"transparent\"}, \"axis\": {\"labelColor\": \"#F5F5F5\", \"titleColor\": \"#F5F5F5\", \"labelFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"titleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"gridColor\": \"#3A3A3A\", \"domainColor\": \"#E6E6E6\", \"tickColor\": \"#E6E6E6\"}, \"legend\": {\"labelColor\": \"#F5F5F5\", \"titleColor\": \"#F5F5F5\", \"labelFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"titleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\"}, \"title\": {\"color\": \"#F5F5F5\", \"subtitleColor\": \"#C4C4C4\", \"font\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\", \"subtitleFont\": \"IBM Plex Sans, Helvetica, Arial, sans-serif\"}, \"range\": {\"category\": [\"#E69F00\", \"#56B4E9\", \"#009E73\", \"#F0E442\", \"#0072B2\", \"#D55E00\", \"#CC79A7\", \"#FFFFFF\"], \"heatmap\": [\"#6BAED6\", \"#9ECAE1\", \"#C6DBEF\", \"#DEEBF7\", \"#F7FBFF\"], \"diverging\": [\"#EF8A62\", \"#FDDBC7\", \"#F7F7F7\", \"#D1E5F0\", \"#67A9CF\"]}}}")


def config():
    return _CONFIG


def register():
    import altair as alt

    alt.themes.register("dark", config)
    return config
