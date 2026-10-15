import { Route, Routes } from "react-router-dom";
import Home from "./pages/public/Home";
import Login from "./pages/public/Login";
import Contact from "./pages/public/Contact.jsx";
import ForgotPassword from "./pages/public/ForgotPassword.jsx";
import ResetPassword from "./pages/public/ResetPassword.jsx";

const App = () => {
  return (
    <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/contact" element={<Contact/>}/>
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password/:code" element={<ResetPassword />} />
    </Routes>
  );
};

export default App;
