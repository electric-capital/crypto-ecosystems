-- 2025-10-13T17:40:00Z add_anoma_sdk_gov_round2
-- SDK/examples + chain metadata + governance/token + tooling/ZK (all public under `anoma`)

-- SDK & Examples
repadd Anoma https://github.com/anoma/namada-sdkjs-examples       #sdk #example
repadd Anoma https://github.com/anoma/namada-sdkjs-node-examples  #sdk #example
repadd Anoma https://github.com/anoma/counter-example             #example #demo
repadd Anoma https://github.com/anoma/counter-web                 #example #demo

-- Chain metadata
repadd Anoma https://github.com/anoma/namada-chain-registry       #chain-registry #metadata

-- Governance & Token
repadd Anoma https://github.com/anoma/namada-governance-upgrades  #governance #wasm
repadd Anoma https://github.com/anoma/token                       #token #smart-contract

-- Tooling / ZK / Local
repadd Anoma https://github.com/anoma/evm-protocol-adapter        #smart-contract #adapter
repadd Anoma https://github.com/anoma/arm-risc0                   #zkvm #arm #research
repadd Anoma https://github.com/anoma/anoma-local-domain          #devtool #local
repadd Anoma https://github.com/anoma/research                    #research
