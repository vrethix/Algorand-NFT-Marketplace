import base64
from typing import Optional

from algosdk.future.transaction import SignedTransaction
from algosdk.v2client import algod
from typing import List, Tuple, Dict, Any, Optional, Union
from base64 import b64decode
from algosdk.v2client.algod import AlgodClient
from pyteal import compileTeal, Mode, Expr


class NetworkInteraction:

    @staticmethod
    def wait_for_confirmation(client: algod.AlgodClient, txid):
        """
        Utility function to wait until the transaction is
        confirmed before proceeding.
        """
        last_round = client.status().get('last-round')
        txinfo = client.pending_transaction_info(txid)
        while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
            print("Waiting for confirmation")
            last_round += 1
            client.status_after_block(last_round)
            txinfo = client.pending_transaction_info(txid)
        print(f"Transaction {txid} confirmed in round {txinfo.get('confirmed-round')}.")
        return txinfo

    @staticmethod
    def get_default_suggested_params(client: algod.AlgodClient):
        """
        Gets default suggested params with flat transaction fee and fee amount of 1000.
        :param client:
        :return:
        """
        suggested_params = client.suggested_params()

        suggested_params.flat_fee = True
        suggested_params.fee = 1000

        return suggested_params

    @staticmethod
    def submit_asa_creation(client: algod.AlgodClient, transaction: SignedTransaction):
        """
        Submits a ASA creation transaction to the network. If the transaction is successful the ASA's id is returned.
        :param client:
        :param transaction:
        :return:
        """
        txid = client.send_transaction(transaction)

        NetworkInteraction.wait_for_confirmation(client, txid)

        try:
            ptx = client.pending_transaction_info(txid)
            return ptx["asset-index"], txid
        except Exception as e:
            # TODO: Proper logging needed.
            print(e)
            print('Unsuccessful creation of Algorand Standard Asset.')

    @staticmethod
    def submit_transaction(client: algod.AlgodClient, transaction: SignedTransaction) -> Optional[str]:
        txid = client.send_transaction(transaction)

        NetworkInteraction.wait_for_confirmation(client, txid)

        return txid

    @staticmethod
    def compile_program(client: algod.AlgodClient, source_code):
        """
        :param client: algorand client
        :param source_code: teal source code
        :return:
            Decoded byte program
        """
        compile_response = client.compile(source_code)
        return base64.b64decode(compile_response['result'])


class PendingTxnResponse:
    def __init__(self, response: Dict[str, Any]) -> None:
        self.poolError: str = response["pool-error"]
        self.txn: Dict[str, Any] = response["txn"]

        self.applicationIndex: Optional[int] = response.get("application-index")
        self.assetIndex: Optional[int] = response.get("asset-index")
        self.closeRewards: Optional[int] = response.get("close-rewards")
        self.closingAmount: Optional[int] = response.get("closing-amount")
        self.confirmedRound: Optional[int] = response.get("confirmed-round")
        self.globalStateDelta: Optional[Any] = response.get("global-state-delta")
        self.localStateDelta: Optional[Any] = response.get("local-state-delta")
        self.receiverRewards: Optional[int] = response.get("receiver-rewards")
        self.senderRewards: Optional[int] = response.get("sender-rewards")

        self.innerTxns: List[Any] = response.get("inner-txns", [])
        self.logs: List[bytes] = [b64decode(l) for l in response.get("logs", [])]


def waitForTransaction(
    client: AlgodClient, txID: str, timeout: int = 10
) -> PendingTxnResponse:
    lastStatus = client.status()
    lastRound = lastStatus["last-round"]
    startRound = lastRound

    while lastRound < startRound + timeout:
        pending_txn = client.pending_transaction_info(txID)

        if pending_txn.get("confirmed-round", 0) > 0:
            return PendingTxnResponse(pending_txn)

        if pending_txn["pool-error"]:
            raise Exception("Pool error: {}".format(pending_txn["pool-error"]))

        lastStatus = client.status_after_block(lastRound + 1)

        lastRound += 1

    raise Exception(
        "Transaction {} not confirmed after {} rounds".format(txID, timeout)
    )


def fullyCompileContract(client: AlgodClient, contract: Expr) -> bytes:
    teal = compileTeal(contract, mode=Mode.Application, version=5)
    response = client.compile(teal)
    return b64decode(response["result"])


def decodeState(stateArray: List[Any]) -> Dict[bytes, Union[int, bytes]]:
    state: Dict[bytes, Union[int, bytes]] = dict()

    for pair in stateArray:
        key = b64decode(pair["key"])

        value = pair["value"]
        valueType = value["type"]

        if valueType == 2:
            # value is uint64
            value = value.get("uint", 0)
        elif valueType == 1:
            # value is byte array
            value = b64decode(value.get("bytes", ""))
        else:
            raise Exception(f"Unexpected state type: {valueType}")

        state[key] = value

    return state


def getAppGlobalState(
    client: AlgodClient, appID: int
) -> Dict[bytes, Union[int, bytes]]:
    appInfo = client.application_info(appID)
    return decodeState(appInfo["params"]["global-state"])


def getBalances(client: AlgodClient, account: str) -> Dict[int, int]:
    balances: Dict[int, int] = dict()

    accountInfo = client.account_info(account)

    # set key 0 to Algo balance
    balances[0] = accountInfo["amount"]

    assets: List[Dict[str, Any]] = accountInfo.get("assets", [])
    for assetHolding in assets:
        assetID = assetHolding["asset-id"]
        amount = assetHolding["amount"]
        balances[assetID] = amount

    return balances


def getLastBlockTimestamp(client: AlgodClient) -> Tuple[int, int]:
    status = client.status()
    lastRound = status["last-round"]
    block = client.block_info(lastRound)
    timestamp = block["block"]["ts"]

    return block, timestamp