from utils import get_algod_client
from services.nft_service import NFTService
from services.nft_marketplace import NFTMarketplace
from account import Account
import hashlib
import json
algod_url = "https://testnet-algorand.api.purestake.io/ps2"
algod_api_key = "c6zlIAzzGE9WldEGPxkt847b0PcR2QYs87aHr5rz"
    
client = get_algod_client(algod_url, algod_api_key)
user1 = {
#    'mnemonic': "strategy device nuclear fan venture produce journey hip possible front weapon ride agent lens finger find strategy little swift valley hand crazy swing absorb clog",
    'mnemonic': "august blanket client borrow magnet doll village crush same come garage illegal oven mechanic path effort truck planet tank resource thank supply solid about dinner",
    'address' : "O22REHHCLB5JDPDTQKOLQVMDMJZZC5HNKDTE2M2JPMUO53JOI5ZL3CZFOM",
}

user2 = {
#    'mnemonic': "inside wreck jewel fence feature negative game car aerobic hip kidney test foot antique kind snow tackle creek school loyal type action napkin able female",
    'mnemonic': "tip fatal stomach poet glow subject genre bundle vital napkin budget recycle will work news sting eagle venture radio smile cigar where jewel above hip",
    'address' : "A7MKKYFAWRPB4YGYE7OX5RUOU6NGBBLHNLHPZ7LIUDYIWC7O546UPSIQDI",
}

admin = Account.from_mnemonic(user1["mnemonic"])
print(admin.get_address())
        
buyer = Account.from_mnemonic(user2["mnemonic"])
print(buyer.get_address())

admin_addr = admin.get_address()
admin_pk = admin.get_private_key()

buyer_addr = buyer.get_address()
buyer_pk = buyer.get_private_key()


nft_service = NFTService(nft_creator_address=admin_addr,
                         nft_creator_pk=admin_pk,
                         client=client,
                         nft_url = "https://ipfs.io/ipfs/QmZr8EXf29iBeiJpEJoYFK6izcM4SYHHeqwgC1XVNXr8BC",
                         asset_name="Algobot",
                         unit_name="Algobot")


info = {
    "name": "PYTHONZ",
    "description": "DEV's Artwork",
    "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQzERqpiBq1uTAsaX78EwVtjGUuae-XMENXiw&usqp=CAU.png",
    "image_integrity": "sha256-/tih/7ew0eziEZIVD4qoTWb0YrElAuRG3b40SnEstyk=",
    "properties": {
        "simple_property": "TEST NFTs",
        "rich_property": {
            "name": "TEST",
            "value": "1",
            "display_value": "1",
            "class": "emphasis",
            "css": {
                "color": "#ffffff",
                "font-weight": "bold",
                "text-decoration": "underline"
            }
        },
        "array_property": {
            "name": "Artwork",
            "value": [1, 2, 3, 4],
            "class": "emphasis"
        }
    }
}


metadataStr = json.dumps(info)

print(metadataStr)

hash = hashlib.new("sha512_256")
hash.update(b"arc0003/amj")
hash.update(metadataStr.encode("utf-8"))
metadatahash = hash.digest()

print (metadatahash)

nft_service.create_nft(metadatahash)

nft_marketplace_service = NFTMarketplace(admin_pk=admin_pk,
                                         admin_address=admin_addr,
                                         client=client,
                                         nft_id=nft_service.nft_id)

nft_marketplace_service.app_initialization(nft_owner_address=admin_addr)

nft_service.change_nft_credentials_txn(escrow_address=nft_marketplace_service.escrow_address)

nft_marketplace_service.initialize_escrow()
nft_marketplace_service.fund_escrow()
nft_marketplace_service.make_sell_offer(sell_price=100000, nft_owner_pk=admin_pk)

nft_service.opt_in(buyer_pk)

nft_marketplace_service.buy_nft(nft_owner_address=admin_addr,
                                buyer_address=buyer_addr,
                                buyer_pk=buyer_pk,
                                buy_price=100000)
