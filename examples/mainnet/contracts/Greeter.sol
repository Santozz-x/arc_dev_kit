// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Minimal example contract for examples/mainnet/10_deploy_contract.py.
contract Greeter {
    string public greeting;

    constructor(string memory _greeting) {
        greeting = _greeting;
    }

    function setGreeting(string memory _greeting) external {
        greeting = _greeting;
    }
}
