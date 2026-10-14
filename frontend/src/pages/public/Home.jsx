import {useNavigate, Link} from "react-router-dom";

const Home = () => {
  const navigate = useNavigate()


  return <div>
    <nav>
      <Link to="/login">Login</Link>
    </nav>
  </div>;
};

export default Home;
