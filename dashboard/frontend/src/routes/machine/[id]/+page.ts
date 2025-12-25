/**
 * Machine Detail page - load machine ID from route params.
 */

export const prerender = false;

export function load({ params }: { params: { id: string } }) {
	return {
		id: params.id
	};
}
