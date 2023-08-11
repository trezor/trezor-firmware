from typing import TYPE_CHECKING

from trezor.ui.layouts import confirm_output, confirm_properties

if TYPE_CHECKING:
    from typing import Awaitable


async def show_parsed_message(
    parsed_msg: dict
) -> None:
    
    for instruction in parsed_msg["instructions"]:
        await confirm_properties(
            "builder",
            "{0}\n{1}".format(instruction["program_name"], instruction["name"]),
            [("Teszt", "Value")]
        )

    # await confirm_properties(
    #     "create_account",
    #     "Create Account 1",
    #     (
    #         ("Lamports", "lamport value"),
    #         ("Space", "space rquired"),
    #         ("Owner", "owner pub key")
    #     )
    # )
    # await confirm_properties(
    #     "create_account",
    #     "Create Account 2",
    #     (
    #         ("Lamports", "lamport value"),
    #         ("Space", "space rquired"),
    #         ("Owner", "owner pub key"),
    #         ("Funding Account", "Funding pub key"),
    #         ("New Account", "New account pub key"),
    #     )
    # )

    # br_type: str,
    # title: str,
    # props: Iterable[PropertyType],    --> PropertyType = tuple[str | None, str | bytes | None]
    # hold: bool = False,
    # br_code: ButtonRequestType = ButtonRequestType.ConfirmOutput,


# {
#     'blockhash': 'c431a67912025e732b884206953b0a61c715c06930ace072ef71588529106ad1', 
#     'instructions': [
#         {
#             'name': 'CreateAccountWithSeed', 
#             'parameters': [
#                 {'name': 'base', 'value': 'c80f8b50107e9f3e3c16a661b8c806df454a6deb293d5e8730a9d28f2f4998c6', 'type': 'Pubkey'},
#                 {'name': 'seed', 'value': 'stake:0', 'type': 'String'},
#                 {'name': 'lamports', 'value': '0000000000989680', 'type': 'u64'}, 
#                 {'name': 'space', 'value': '00000000000000c8', 'type': 'u64'}, 
#                 {'name': 'owner', 'value': '06a1d8179137542a983437bdfe2a7ab2557f535c8a78722b68a49dc000000000', 'type': 'Pubkey'}
#             ], 
#             'data_length': 99, 
#             'accounts': [
#                 'c80f8b50107e9f3e3c16a661b8c806df454a6deb293d5e8730a9d28f2f4998c6', 
#                 'f8359ad2e63b4c9969d63b72c8caa50de8a5bce88c32b5d59c062b491dda86af'
#             ], 
#             'program_name': 'System program', 
#             'program_id': '0000000000000000000000000000000000000000000000000000000000000000'
#         },
#         'header': {
#             'required': 1, 
#             'notrequired': 3, 
#             'readonly': 0
#         }, 
#         'accounts': [
#             'c80f8b50107e9f3e3c16a661b8c806df454a6deb293d5e8730a9d28f2f4998c6', 
#             'f8359ad2e63b4c9969d63b72c8caa50de8a5bce88c32b5d59c062b491dda86af', 
#             '0000000000000000000000000000000000000000000000000000000000000000', 
#             '06a1d8179137542a983437bdfe2a7ab2557f535c8a78722b68a49dc000000000', 
#             '06a7d517192c5c51218cc94c3d4af17f58daee089ba1fd44e3dbd98a00000000'
#         ]
#     }
