const Footer = () => (
  <footer className="bg-light py-4 mt-5">
    <div className="container d-flex flex-wrap justify-content-between">
      <div className="mb-3">
        <h6>CitySnap</h6>
        <small className="text-muted">
          Сервис для получения исторической информации о зданиях
        </small>
      </div>
      <div>
        <h6>Поддержка</h6>
        <ul className="list-unstyled mb-0">
          <li>
            <a
              href="https://github.com/sbaldin/case-check-city-snap/blob/main/README.md"
              className="text-decoration-none"
              target="_blank"
              rel="noreferrer"
            >
              Помощь
            </a>
          </li>
          <li>
            <a href="https://github.com/sbaldin" className="text-decoration-none" target="_blank" rel="noreferrer">
              Контакты
            </a>
          </li>
          <li>
            <a
              href="https://github.com/sbaldin/case-check-city-snap/blob/main/README.md"
              className="text-decoration-none"
              target="_blank"
              rel="noreferrer"
            >
              Как это работает
            </a>
          </li>
        </ul>
      </div>
    </div>
    <div className="text-center mt-3 small text-muted">© 2025 CitySnap. Все права защищены.</div>
  </footer>
);

export default Footer;
