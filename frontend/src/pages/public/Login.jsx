import { useState, useEffect } from "react";
import GoogleAuthButton from "../../components/GoogleAuthButton";

const Login = () => {
  return (
    <form>
      <input type="text" name="username_or_email" />
      <input type="password" name="password" />
      <GoogleAuthButton />
      <button>Login</button>
    </form>
  );
};

export default Login;
