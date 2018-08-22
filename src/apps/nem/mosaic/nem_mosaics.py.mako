# generated from nem_mosaics.py.mako
# do not edit manually!
<%
ATTRIBUTES = (
    "name",
    "ticker",
    "namespace",
    "mosaic",
    "divisibility",
    "levy",
    "fee",
    "levy_namespace",
    "levy_mosaic",
    "networks",
)
%>\

mosaics = [
% for m in supported_on("trezor2", nem):
<% m.ticker = " " + m.ticker %>\
    {
    % for attr in ATTRIBUTES:
        % if attr in m:
        "${attr}": ${black_repr(m[attr])},
        % endif
    % endfor
    },
% endfor
]
