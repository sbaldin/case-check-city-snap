import Footer from './components/Footer';
import Header from './components/Header';
import AppRouter from './router/AppRouter';

const App = () => (
  <div className="d-flex flex-column min-vh-100">
    <Header />
    <div className="flex-grow-1">
      <AppRouter />
    </div>
    <Footer />
  </div>
);

export default App;
