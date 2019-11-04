# generated from nem2_mosaics.py.mako
# do not edit manually!

# TODO: ensure all required mosaic fields are accounted for
<%
ATTRIBUTES = (
    "id",
    "name",
    "divisibility",
    "networks",
)
%>\

mosaics = [
% for m in supported_on("trezor2", nem2):
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
