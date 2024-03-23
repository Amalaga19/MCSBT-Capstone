import React, { useState, useEffect } from "react";
import {  Button,  Form,  Card,  Container,  Row,  Col,  Alert,  Table,  Modal,} from "react-bootstrap";
import "bootstrap/dist/css/bootstrap.min.css";
import "./App.css";
import { Chart } from "react-chartjs-2";
import "chart.js/auto";

function App() {
  const [username, setUsername] = useState(localStorage.getItem("loggedInUser") || "");
  const [password, setPassword] = useState("");
  const [portfolio, setPortfolio] = useState({});
  const [portfolioTotal, setPortfolioTotal] = useState(0);
  const [error, setError] = useState("");
  const [loggedIn, setLoggedIn] = useState(!!localStorage.getItem("loggedInUser"));
  const [selectedTicker, setSelectedTicker] = useState("");
  const [priceHistory, setPriceHistory] = useState([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [newTicker, setNewTicker] = useState("");
  const [newQuantity, setNewQuantity] = useState(0);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [updateQuantity, setUpdateQuantity] = useState(0);
  const [currentUpdatingStock, setCurrentUpdatingStock] = useState("");
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showGraph, setShowGraph] = useState(false);

  //const backendUrl = "http://localhost:5000"; //this is for testing locally
  const backendUrl = "https://mcsbt-integration-ams.ew.r.appspot.com"; //this is for deployment

  useEffect(() => {
    if (loggedIn) fetchPortfolio();
  }, [loggedIn, username, portfolioTotal]);

  const chartData = { // Chart data for price history
    labels: priceHistory.map(([date, price]) => date),
    datasets: [{label: "Price (USD)",data: priceHistory.map(([date, price]) => price)},],};

  const chartOptions = { // Chart Customization
    animation: true,
    plugins: {
      legend: {
        display: false,
      },
    },
    borderColor: "teal",
    fill: true,
    scales: {
      y: {
        beginAtZero: false,
      },
    },
  };

  const fetchPortfolio = async () => { // Fetches the user's portfolio
    if (!username) return;
    try {
      const response = await fetch(`${backendUrl}/api/portfolio/?username=${username}`,{ credentials: "include" });
      if (response.ok) {
        const data = await response.json();
        setPortfolio(data.stocks_owned);
        setPortfolioTotal(data.total_value);
      } else {
        const data = await response.json();
        throw new Error(data.message || "Failed to load portfolio.");
      }
    } catch (error) {
      setError(error.message);
    }
  };

  const login = async (e) => { //Handles user login
    e.preventDefault();
    try {
      const response = await fetch(`${backendUrl}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem("loggedInUser", username);
        setLoggedIn(true);
      } else {
        throw new Error(data.message || "Failed to log in.");
      }
    } catch (error) {
      setError(error.message);
      setLoggedIn(false);
    }
  };

  const logout = async () => { //Handles user logout and clears local storage
    try {
      await fetch(`${backendUrl}/logout`, {
        method: "GET",
        credentials: "include",
      });
      localStorage.removeItem("loggedInUser");
      setLoggedIn(false);
      setUsername("");
      setPassword("");
    } catch (error) {
      console.error("Error logging out: ", error);
    }
  };

  const fetchTickerPriceHistory = async () => { // Fetches the price history of a stock between two dates
    const today = new Date().toISOString().split("T")[0];
    let monthAgo = new Date();
    monthAgo.setMonth(monthAgo.getMonth() - 1);
    monthAgo = monthAgo.toISOString().split("T")[0];

    const effectiveStartDate = startDate || monthAgo; // Default to 1 month ago if the user doesn't specify a start date
    const effectiveEndDate = endDate || today; // Default to today if the user doesn't specify an end date

    try {
      const response = await fetch(`${backendUrl}/api/portfolio/${selectedTicker}?start_date=${effectiveStartDate}&end_date=${effectiveEndDate}`);
      if (response.ok) {
        const data = await response.json();
        if (Object.keys(data).length === 0) {
          setError("No data available for the selected date range.");
          setPriceHistory([]);
          return;
        }
        const sortedData = Object.entries(data).sort((a, b) => new Date(b[0]) - new Date(a[0])); // Sort to ensure most recent date is first
        setPriceHistory(sortedData);
      } else {
        const data = await response.json();
        if (data.message) {
          setError(`${data.message}.`);
        } else {
          throw new Error(
            data.message || "Failed to load ticker price history."
          );
        }
      }
    } catch (error) {
      setError(error.message);
    }
  };

  const updateUserPortfolio = async (action, stock, quantity) => { // Updates the user's portfolio based on the action (add, remove, modify)
    try {
      const response = await fetch(`${backendUrl}/update_user`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, action, stock, quantity }),
      });
      const data = await response.json();
      if (response.ok) {
        alert(data.message);
        fetchPortfolio();
      } else {
        throw new Error(data.message);
      }
    } catch (error) {
      setError(error.message);
    }
  };

  return (
    <Container>
      {!loggedIn ? ( // If user is not logged in, display login form
        <div className="login-container">
          <h2>Login</h2>
          {error && <Alert variant="danger">{error}</Alert>}
          <Form onSubmit={login}>
            <Form.Group controlId="username">
              <Form.Label>Username</Form.Label>
              <Form.Control
                type="text"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </Form.Group>
            <Form.Group controlId="password">
              <Form.Label>Password</Form.Label>
              <Form.Control
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </Form.Group>
            <Button variant="primary" type="submit">
              Login
            </Button>
          </Form>
        </div>
      ) : ( //if user is logged in, display portfolio
        <>
          <h2>Welcome To Your Portfolio, {username}!</h2>
          <>
            <Row className="align-items-center justify-content-between my-3">
              <Col className="text-right">
                <h3>Total Value: ${portfolioTotal}</h3>
              </Col>
              <Col xs="auto">
                <Button onClick={() => setShowAddModal(true)}>Add Stock</Button>
              </Col>
              <Col xs="auto">
                <Button variant="danger" onClick={logout}>Logout</Button>
              </Col>
            </Row>
          </>
          <row className="justify-content-center">
            <h3>Your Stocks:</h3>
          </row>
          <Row>
            {Object.entries(portfolio).map( // Display each stock in the portfolio as a card, each card has buttons to remove, view price history, and update quantity
              ([ticker, { quantity, price, price_total }]) => (
                <Col key={ticker} md={4} className="mb-4">
                  <Card>
                    <Card.Body>
                      <Card.Title>{ticker}</Card.Title>
                      <Card.Text>
                        Quantity: {quantity}
                        <br />
                        Latest Closing Price: ${price}
                        <br />
                        Total Value: ${price_total}
                      </Card.Text>
                      <div className="d-flex flex-column align-items-center">
                        <Button variant="secondary" onClick={() => updateUserPortfolio("remove", ticker, 0)}>Remove</Button>
                        <Button variant="primary" onClick={() => {setSelectedTicker(ticker); setShowHistoryModal(true);}}>View Price History</Button>
                        <Button variant="warning" onClick={() => {setCurrentUpdatingStock(ticker); setUpdateQuantity(quantity); setShowUpdateModal(true);}}>Update Quantity</Button>
                      </div>
                    </Card.Body>
                  </Card>
                </Col>
              )
            )}
          </Row>
          <Modal show={showAddModal} onHide={() => setShowAddModal(false)}> {/* Modal for adding a stock */}
            <Modal.Header closeButton>
              <Modal.Title>Add Stock</Modal.Title>
            </Modal.Header>
            <Modal.Body>
              <Form>
                <Form.Group>
                  <Form.Label>Enter stock ticker</Form.Label>
                  <Form.Control type="text" value={newTicker} onChange={(e) => setNewTicker(e.target.value)}/>
                </Form.Group>
                <Form.Group>
                  <Form.Label>Enter quantity</Form.Label>
                  <Form.Control type="number" value={newQuantity} onChange={(e) => setNewQuantity(e.target.value)}/>
                </Form.Group>
              </Form>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onClick={() => setShowAddModal(false)}>Close</Button>
              <Button variant="primary" onClick={() => {const quantity = parseInt(newQuantity);if (isNaN(quantity) || quantity <= 0) {
                    alert("Please enter a valid quantity (positive integer). Floats will be truncated");
                  } else {updateUserPortfolio("add", newTicker, quantity);setShowAddModal(false);}}}>Add</Button>
            </Modal.Footer>
          </Modal>
          <Modal show={showUpdateModal} onHide={() => setShowUpdateModal(false)}> {/* Modal for updating stock quantity */}
            <Modal.Header closeButton>
              <Modal.Title>Update Stock Quantity</Modal.Title>
            </Modal.Header>
            <Modal.Body>
              <Form>
                <Form.Group>
                  <Form.Label>
                    Enter new quantity for {currentUpdatingStock}
                  </Form.Label>
                  <Form.Control type="number" value={updateQuantity} onChange={(e) => setUpdateQuantity(e.target.value)}/>
                </Form.Group>
              </Form>
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onClick={() => setShowUpdateModal(false)}>Close</Button>
              <Button variant="primary"   onClick={() => {let quantity = parseInt(updateQuantity);if (isNaN(quantity) || quantity <= 0) {
                    alert("Please enter a valid quantity (positive integer). Floats will be truncated.");
                  } else {updateUserPortfolio("modify",currentUpdatingStock,quantity);setShowUpdateModal(false);}}}>Update</Button>
            </Modal.Footer>
          </Modal>
          <Modal show={showHistoryModal} onHide={() => setShowHistoryModal(false)} size="lg"> {/* Modal for viewing price history either as a table or a graph*/}
            <Modal.Header closeButton>
              <Modal.Title>Price History for {selectedTicker}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
              <Form>
                <Row className="align-items-center">
                  <Col xs="auto">
                    <Form.Group controlId="startDate">
                      <Form.Label>Start Date</Form.Label>
                      <Form.Control type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}/>
                    </Form.Group>
                  </Col>
                  <Col xs="auto">
                    <Form.Group controlId="endDate">
                      <Form.Label>End Date</Form.Label>
                      <Form.Control type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}/>
                    </Form.Group>
                  </Col>
                  <Col xs="auto">
                    <Button variant="primary" onClick={() => {if (new Date(startDate) > new Date(endDate)) {
                          alert("Start date is greater than end date. Range is invalid.");} 
                          else {fetchTickerPriceHistory(selectedTicker, startDate, endDate); setShowGraph(false);}}}>View Table</Button>
                    <Button variant="secondary" onClick={() => { if (new Date(startDate) > new Date(endDate)) {alert("Start date is greater than end date. Range is invalid.");
                        } else {fetchTickerPriceHistory(selectedTicker,startDate,endDate);setShowGraph(true);}}}>View Graph</Button>
                  </Col>
                </Row>
              </Form>
              {showGraph & (priceHistory.length > 0) ? (<Chart type="line" data={chartData} options={chartOptions} />) :
               !showGraph & (priceHistory.length > 0) ? (
                <Table striped bordered hover>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Close Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {priceHistory.map(([date, price]) => (
                      <tr key={date}>
                        <td>{date}</td>
                        <td>${price}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>) : 
                (<div>No price history available.</div>)}
            </Modal.Body>
            <Modal.Footer>
              <Button variant="secondary" onClick={() => { setShowHistoryModal(false); setShowGraph(false); setStartDate(""); setEndDate(""); setSelectedTicker("");}}>Close</Button>
            </Modal.Footer>
          </Modal>
        </>
      )}
    </Container>
  );
}
export default App;
