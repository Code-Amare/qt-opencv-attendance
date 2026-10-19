import {
    createContext,
    useContext,
    useEffect,
    useState,
} from "react"

const ThemeContext = createContext(null)

const ThemeProvider = ({ children }) => {
    const [theme, setTheme] = useState(() => {
        return localStorage.getItem("theme") || "light"
    })

    useEffect(() => {
        const root = document.documentElement

        root.classList.toggle("dark", theme === "dark")

        localStorage.setItem("theme", theme)
    }, [theme])

    const themeToggle = () => {
        setTheme((currentTheme) =>
            currentTheme === "dark" ? "light" : "dark"
        )
    }

    return (
        <ThemeContext.Provider
            value={{
                theme,
                themeToggle,
            }}
        >
            {children}
        </ThemeContext.Provider>
    )
}

export function useTheme() {
    return useContext(ThemeContext)
}

export default ThemeProvider