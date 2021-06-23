{% for section, _ in sections.items() %}
{% if section %}{{section}}{% endif -%}

{% if sections[section] %}

{% for category, val in definitions.items() if category in sections[section] %}

### {{ definitions[category]['name'] }}
{% if definitions[category]['showcontent'] %}
{% for text, values in sections[section][category].items() %}
- {{ text }}  {{ values|reject("eq", "[#noissue]")|join(', ') }}
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}
{% endfor %}
