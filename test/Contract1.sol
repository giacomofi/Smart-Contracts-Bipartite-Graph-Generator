// SPDX-License-Identifier: MIT
pragma solidity ^0.7.6;

import "./Contract2.sol";
import "./Contract3.sol";

contract Contract1 {
    Contract2 contract2;
    Contract3 contract3;

    constructor(Contract2 _contract2, Contract3 _contract3) {
        contract2 = _contract2;
        contract3 = _contract3;
    }

    function func1() public {
        contract2.func2();
        contract3.func3();
    }
}
