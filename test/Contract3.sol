// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

import "./Contract1.sol";
import "./Contract2.sol";

contract Contract3 {
    Contract1 contract1;
    Contract2 contract2;

    constructor(Contract1 _contract1, Contract2 _contract2) {
        contract1 = _contract1;
        contract2 = _contract2;
    }

    function func3() public {
        contract1.func1();
        contract2.func2();
    }
}
