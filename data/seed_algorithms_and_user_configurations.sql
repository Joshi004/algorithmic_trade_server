-- Seed data for new algorithm tables

-- Scanning Algorithms
INSERT INTO scanning_algorithms (name, display_name, description)
VALUES ('UDTS', 'Unidirectional Trading Strategy', '<div>
  <h1>Unidirectional Trading Strategy</h1>
  <p>This strategy focuses on trading in a single direction—either long (buy) or short (sell)—without switching to the opposite side. It aims to capitalize on market trends by maintaining directional bias.</p>
  <p>By specializing in one direction, traders can better analyze market behavior and identify high-probability entry and exit points. This targeted approach enhances decision-making and risk management.</p>
  <p>Note: Unidirectional strategies require thorough backtesting, ongoing monitoring, and sound risk controls to be effective in live markets.</p>
</div>');

-- Initiation Algorithms
INSERT INTO initiation_algorithms (name, display_name, description)
VALUES ('Immediate', 'Immediate Initiation', 'The system initiates a trade immediately upon receiving an instrument from the scanner.');

-- Termination Algorithms
INSERT INTO termination_algorithms (name, display_name, description)
VALUES ('Immediate', 'Immediate Termination', 'The system terminates the trade as soon as the initiator receives the instrument from the scanner.');