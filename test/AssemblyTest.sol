pragma solidity >=0.4.0 <0.6.0;

library GetCode {
    function at(address _addr) public view returns (bytes memory o_code) {
        assembly {
            // retrieve the size of the code, this needs assembly
            let size := extcodesize(_addr)
            // allocate output byte array - this could also be done without assembly
            // by using o_code = new bytes(size)
            o_code := mload(0x40)
            // new "memory end" including padding
            mstore(0x40, add(o_code, and(add(add(size, 0x20), 0x1f), not(0x1f))))
            // store length in memory
            mstore(o_code, size)
            // actually retrieve the code, this needs assembly
            extcodecopy(_addr, add(o_code, 0x20), 0, size)
        }


    }


}

library VectorSum {
    // This function is less efficient because the optimizer currently fails to
    // remove the bounds checks in array access.
    function sumSolidity(uint[] memory _data) public pure returns (uint o_sum) {
        for (uint i = 0; i < _data.length; ++i)
            o_sum += _data[i];
    }

    // We know that we only access the array in bounds, so we can avoid the check.
    // 0x20 needs to be added to an array because the first slot contains the
    // array length.
    function sumAsm(uint[] memory _data) public pure returns (uint o_sum) {
        for (uint i = 0; i < _data.length; ++i) {
            assembly {
                o_sum := add(o_sum, mload(add(add(_data, 0x20), mul(i, 0x20))))
            }
        }
    }

    // Same as above, but accomplish the entire code within inline assembly.
    function sumPureAsm(uint[] memory _data) public pure returns (uint o_sum) {
        assembly {
           // Load the length (first 32 bytes)
           let len := mload(_data)

           // Skip over the length field.
           //
           // Keep temporary variable so it can be incremented in place.
           //
           // NOTE: incrementing _data would result in an unusable
           //       _data variable after this assembly block
           let data := add(_data, 0x20)

           // Iterate until the bound is not met.
           for
               { let end := add(data, mul(len, 0x20)) }
               lt(data, end)
               { data := add(data, 0x20) }
           {
               o_sum := add(o_sum, mload(data))
           }
        }
    }
}

contract C {
    function f(uint x) public view returns (uint b) {
        assembly {
            let v := add(x, 1)
            if eq(x, 0) { revert(0, 0) }

            switch calldataload(4)
            case 0 {
                x := calldataload(0x24)
            }
            default {
                x := calldataload(0x44)
            }
            mstore(0x80, v)
            {
                let y := add(sload(v), 1)
                b := y
            } // y is "deallocated" here
            b := add(b, v)

        } // v is "deallocated" here


    }


}

