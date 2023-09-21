// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

import "./Contract1.sol";
import "./Contract3.sol";

contract Contract2 {
    Contract1 contract1;
    Contract3 contract3;

    constructor(Contract1 _contract1, Contract3 _contract3) {
        contract1 = _contract1;
        contract3 = _contract3;
    }

    function func2() public {
        contract1.func1();
        contract3.func3();
    }
}
