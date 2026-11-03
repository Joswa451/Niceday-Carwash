import { Link } from 'react-router-dom'
import PageHero from '../components/PageHero'

export default function NotFoundPage() {
  return (
    <>
      <PageHero title="Page not found" subtitle="The page you are looking for does not exist." />
      <section className="section">
        <div className="container">
          <div className="empty-state">
            <div className="empty-icon">&#128269;</div>
            <h3>We could not find that page</h3>
            <p>Check the address or head back to the homepage.</p>
            <Link className="btn btn-primary" to="/">
              Back to homepage
            </Link>
          </div>
        </div>
      </section>
    </>
  )
}
